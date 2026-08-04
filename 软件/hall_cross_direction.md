# 霍尔传感器方向检测：二维叉积原理

## 代码

```c
cross = ((int32_t)hall->detect->dir_a_prev * (int32_t)hall->hall_b_raw) - 
        ((int32_t)hall->detect->dir_b_prev * (int32_t)hall->hall_a_raw);
```

## 数学本质

二维叉积（行列式）：

```
cross = x_prev * y_now - y_prev * x_now
      = |A| * |B| * sin(θ)
```

- `(dir_a_prev, dir_b_prev)` — 上一时刻的霍尔方向向量
- `(hall_a_raw, hall_b_raw)` — 当前原始霍尔采样值（两相正交分量）

## 方向判断

| cross | 含义 |
|---|---|
| > 0 | 逆时针（正转），当前向量在上一次左侧 |
| < 0 | 顺时针（反转），当前向量在上一次右侧 |
| = 0 | 共线（静止或翻转 180°） |

## 为什么用 raw 值而不是校正值

注释明确指出：此时 offset 偏置尚未计算（step2 才得出），因此不能使用 `hall_sin` 等校正后的值。

但叉积的**符号**不依赖直流偏置是否消除——只要两路信号的相位关系正确，raw 值足以判定方向。这是利用几何关系绕开标定未完成的问题。
