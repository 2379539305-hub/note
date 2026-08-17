# SEGGER RTT 与 J-Scope 实时观测与调试完全指南

---

## 1. J-Link RTT Viewer 与 J-Scope 的区别与依赖关系

在嵌入式开发中，SEGGER 提供了两套不同维度的实时观测工具：

| 对比维度 | J-Link RTT Viewer (文本终端) | J-Scope HSS 模式 (波形示波器) |
| :--- | :--- | :--- |
| **主要功能** | 高速文本日志滚动输出、状态打印、按键交互 | 类似虚拟示波器，实时绘制连续动态物理量曲线 |
| **MCU 源码依赖** | **必须移植** 4 个 RTT 源码文件 + 调用 `SEGGER_RTT_printf()` | **不需要** 任何 RTT 源码文件，仅需定义 **全局变量** |
| **前置必要条件** | • 移植 RTT 驱动并调用打印函数<br>• MCU 运行初始化代码 | • 代码中声明 **全局变量**（如 `g_scope_motor1`）<br>• J-Scope 加载编译生成的 **`.axf` 符号文件** |
| **工作原理** | MCU 把字符串格式化写入 RAM 的环形缓冲区（Ring Buffer），J-Link 后台读取并解析为文本 | J-Link 根据 `.axf` 符号表直接通过 SWD 硬件总线直接读取全局变量在 RAM 中的物理地址 |
| **CPU 资源占用** | 极低（微秒级 `memcpy` 内存拷贝） | **绝对零 CPU 占用**（MCU 无需执行任何发送/打印指令） |

> **总结**：
> - 想在 **RTT Viewer** 中打印文本日志 -> **必须移植 4 个 RTT 文件**。
> - 想在 **J-Scope** 中看波形曲线（HSS 模式） -> **不需要 RTT 文件**，只要有**全局变量**并加载 **`.axf`** 即可。
> - 本项目中已经将两套功能全部打通，既可在 RTT Viewer 中查看文本，也可在 J-Scope 中直接查看连续电流曲线。

---

## 2. 工程文件结构与配置

本项目中已将 SEGGER RTT 组件存放在 `System/` 目录下，并在 Keil MDK 中配置编译：

| 文件名 | 路径 | 作用与功能说明 |
| :--- | :--- | :--- |
| **`SEGGER_RTT.h`** | `System/SEGGER_RTT.h` | RTT 核心头文件，定义控制块结构体、API 接口及终端颜色宏 |
| **`SEGGER_RTT_Conf.h`** | `System/SEGGER_RTT_Conf.h` | 配置文件，可调整缓冲区大小、通道数量及阻塞/非阻塞模式 |
| **`SEGGER_RTT.c`** | `System/SEGGER_RTT.c` | RTT 底层环形缓冲区读写与初始化实现 |
| **`SEGGER_RTT_printf.c`** | `System/SEGGER_RTT_printf.c` | 精简、无依赖的高性能嵌入式 `printf` 格式化实现 |

---

## 3. RTT 常用 API 接口速查

在需要打印的文件中引入头文件：
```c
#include "SEGGER_RTT.h"
```

### 3.1 初始化接口
```c
void SEGGER_RTT_Init(void);
```
- **说明**：初始化 RTT 控制块 `_SEGGER_RTT`，重置上下行缓冲区的读写偏移量。
- **位置**：通常在 `main()` 函数的最开始调用一次。

### 3.2 格式化输出接口 (`SEGGER_RTT_printf`)
```c
int SEGGER_RTT_printf(unsigned BufferIndex, const char * sFormat, ...);
```
- **参数**：
  - `BufferIndex`：缓冲区通道索引，默认终端使用 `0`（即 Terminal 0）。
  - `sFormat`：格式化字符串，支持 `%d`, `%u`, `%x`, `%X`, `%s`, `%c` 以及宽度对齐修饰符（如 `%4u`, `%03u`, `%-10s` 等）。
- **示例**：
  ```c
  SEGGER_RTT_printf(0, "System Booted, Tick: %u ms\r\n", system_tick);
  SEGGER_RTT_printf(0, "ADC: %4u | Voltage: %4u mV\r\n", adc_raw, voltage_mv);
  ```

### 3.3 快速字符串与字符输出
```c
unsigned SEGGER_RTT_WriteString(unsigned BufferIndex, const char* s);
unsigned SEGGER_RTT_PutChar(unsigned BufferIndex, char c);
unsigned SEGGER_RTT_Write(unsigned BufferIndex, const void* pBuffer, unsigned NumBytes);
```
- **说明**：无需格式化转换时，直接使用 `SEGGER_RTT_WriteString` 效率最高。

### 3.4 接收上位机输入（键盘交互）
```c
int SEGGER_RTT_HasKey(void); // 查询是否有按键输入 (1: 有, 0: 无)
int SEGGER_RTT_GetKey(void);  // 读取一个字符，无按键时返回 -1
```
- **示例**：
  ```c
  if(SEGGER_RTT_HasKey())
  {
      int c = SEGGER_RTT_GetKey();
      if(c == '1') {
          // 触发模式1
      }
  }
  ```

---

## 4. 格式化输出实战技巧

### 4.1 浮点数/电流值的轻量格式化（推荐做法）
嵌入式简易版 `printf` 通常不包含体积庞大且耗费栈空间的浮点库。可以通过**整数模拟定点小数**的方式输出：
```c
uint32_t curr_ma = 1250; // 1250 mA = 1.250 A

// 使用 %u.%03u 分别打印整数部分和小数部分
SEGGER_RTT_printf(0, "Current: %5u mA (%u.%03u A)\r\n", 
                  curr_ma, curr_ma / 1000, curr_ma % 1000);
// 输出结果: Current:  1250 mA (1.250 A)
```

### 4.2 ANSI 彩色终端输出
RTT 支持 ANSI 转义序列，可在 J-Link RTT Viewer 中以不同颜色显示警告或状态：
```c
// 绿色成功提示
SEGGER_RTT_printf(0, RTT_CTRL_TEXT_BRIGHT_GREEN "[OK] Motor Init Success" RTT_CTRL_RESET "\r\n");

// 红色警告提示
SEGGER_RTT_printf(0, RTT_CTRL_TEXT_BRIGHT_RED "[WARN] Overcurrent Detected: %u mA" RTT_CTRL_RESET "\r\n", curr_ma);

// 黄色信息提示
SEGGER_RTT_printf(0, RTT_CTRL_TEXT_BRIGHT_YELLOW "[INFO] Mode Changed: %u" RTT_CTRL_RESET "\r\n", mode);
```

---

## 5. 电机 ADC 换算真实电流公式 (基于原理图 SS6548D_V0.1)

### 硬件电路参数
- **驱动芯片**：U2 SS6548D
- **采样电阻**：`R14 (0.2Ω)` 与 `R15 (0.2Ω)` 并联接地 -> `R_shunt = 0.10 Ω (100 mΩ)`
- **运放放大**：直接通过 `R12 (1k)` + `C12 (100nF)` 滤波接入 MCU `PC6 / ADC_IN11` -> `Gain = 1.0`
- **供电基准**：U4 AMS1117-3.3V 提供 `Vref = 3.3V = 3300 mV`
- **ADC 满量程**：12 位 ADC，范围 `0 ~ 4095`

### 计算公式
```text
采样引脚电压 (mV) = (ADC_Value * 3300.0) / 4095.0
电机真实电流 (mA) = 采样引脚电压 (mV) / 0.10 Ω = (ADC_Value * 33000.0) / 4095.0
比例系数           = 1 LSB ≈ 8.0586 mA (即 Current_mA = ADC_Value * 8.0586)
```

---

## 6. 上位机软件配置与使用

### 6.1 J-Link RTT Viewer 配置（看文本输出）
1. 打开 `J-Link RTT Viewer`。
2. **Specify Target Device**：选择 `FM33LC04X` 或通用 `Cortex-M0+`。
3. **Target Interface**：选择 `SWD`，速度推荐 `2000 kHz` ~ `4000 kHz`。
4. **RTT Control Block**：选择 **`Auto Detection`**。
5. 连接后切换到 **Terminal 0**，即可实时看到每 100ms 滚动的 ADC 和电流数据。

### 6.2 J-Scope 配置（看动态示波器波形）
1. 打开 `J-Scope`（独立安装软件）。
2. 选择 **`HSS (High-Speed Sensor)`** 模式。
3. **Target Device**：直接选择 **`Cortex-M0+`**（国产第三方芯片无需专有驱动，直接选 ARM 内核即可）。
4. **Target Interface**：选择 **`SWD`**。
5. **ELF/AXF File**：浏览选择本工程编译出的 `Project\Objects\Template.axf`。
6. 添加全局观测变量：
   - `g_scope_motor1.adc_raw`（原始 ADC 码值）
   - `g_scope_motor1.current_ma`（真实电流，单位 mA）
   - `g_scope_motor1.current_a`（真实电流，单位 A）
7. 点击 **Start Recording** 开始捕获波形。

---

## 7. 常见问题排查 (FAQ)

- **Q1: 为什么 J-Scope 无法检测/搜索到复旦微芯片？**
  - **解答**：SEGGER 默认设备库未收录复旦微芯片名称。但 HSS 模式仅需通过 SWD 读取 RAM，**直接在 Target Device 中选择 `Cortex-M0+` 即可 100% 正常使用**。

- **Q2: 打开 J-Scope 提示连接失败或 Device in use？**
  - **解答**：J-Link 的 SWD 调试接口同一时刻只能被一个上位机独占。使用 J-Scope 时，请先关闭/断开 J-Link RTT Viewer 和 Keil Debug 在线调试。

- **Q3: 缓冲区满时会卡死 MCU 吗？**
  - **解答**：不会。`SEGGER_RTT_Conf.h` 默认配置为 `SEGGER_RTT_MODE_NO_BLOCK_SKIP`（非阻塞丢弃模式），若上位机未连接或缓冲区已满，MCU 会直接跳过，绝不卡死系统。
