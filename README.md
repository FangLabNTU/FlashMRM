# MRM Transition Optimization Tool

MRM (Multiple Reaction Monitoring) 转换优化工具，用于质谱分析中的离子对优化。

## 项目结构

```
.
├── config.py                  # 配置类，包含所有参数设置
├── data_loader.py             # 数据加载模块
│   ├── DataLoader            # 基础数据加载器
│   └── LazyFileLoader        # 延迟文件加载器（内存优化）
├── interference_calculator.py # 干扰计算模块
│   ├── InterferenceCalculatorQE   # QE方法干扰计算器
│   └── InterferenceCalculatorNIST # NIST方法干扰计算器
├── ion_optimizer.py          # 离子对优化模块
│   ├── IonPairOptimizerQE    # QE方法离子对优化器
│   └── IonPairOptimizerNIST  # NIST方法离子对优化器
├── memory_monitor.py          # 内存监控模块
│   └── MemoryMonitor         # 内存使用监控器
├── mrm_optimizer.py          # 主优化器模块
│   └── MRMOptimizer          # 主优化器类
├── validator.py              # 验证模块
│   └── InterferenceDBValidator # 干扰库格式验证器
├── main.py                   # 主入口文件
└── __init__.py               # 包初始化文件
```

## 模块说明

### config.py
包含所有配置参数，使用 dataclass 定义，便于管理和修改。

### data_loader.py
- **DataLoader**: 基础数据加载器，用于加载CSV文件
- **LazyFileLoader**: 延迟加载器，按需查询数据，减少内存占用

### interference_calculator.py
- **InterferenceCalculatorQE**: QE方法的干扰计算
- **InterferenceCalculatorNIST**: NIST方法的干扰计算

### ion_optimizer.py
- **IonPairOptimizerQE**: QE方法的离子对优化
- **IonPairOptimizerNIST**: NIST方法的离子对优化

### memory_monitor.py
内存使用监控，跟踪程序运行过程中的内存占用情况。

### mrm_optimizer.py
主优化器类，协调各个模块完成MRM转换优化任务。

### validator.py
干扰库格式验证器，用于验证用户上传的自定义干扰库格式是否正确。

### main.py
命令行入口，解析参数并启动优化流程。

## 使用方法

### 基本使用

```bash
# 使用NIST方法处理375个化合物
python main.py --intf-db nist --max-compounds 375

# 使用QE方法处理单个化合物
python main.py --intf-db qe --single-compound --inchikey "YOUR_INCHIKEY"

# 指定输出文件
python main.py --output my_results.csv
```

### 使用自定义干扰库

用户可以上传自己的干扰库文件或文件夹供计算使用：

```bash
# 使用自定义干扰库（NIST格式）
python main.py --intf-db nist --custom-intf-db /path/to/your/interference_db.csv

# 使用自定义干扰库文件夹（包含多个CSV文件）
python main.py --intf-db nist --custom-intf-db /path/to/your/interference_db_folder

# 使用自定义干扰库（QE格式）
python main.py --intf-db qe --custom-intf-db /path/to/your/qe_interference_db.csv

# 跳过验证（不推荐，仅在确认格式正确时使用）
python main.py --intf-db nist --custom-intf-db /path/to/db --skip-validation
```

#### 干扰库格式要求

**NIST方法干扰库必需列：**
- `InChIKey`
- `PrecursorMZ`
- `RT`
- `MSMS`
- `NCE`
- `CE`
- `Ion_mode`
- `Precursor_type`

**QE方法干扰库必需列：**
- `Alignment ID`
- `Average Mz`
- `Average Rt(min)`
- `CE`
- `MS/MS spectrum`

程序会自动验证用户上传的干扰库格式，确保包含所有必需的列。

## 依赖项

- pandas
- numpy
- tqdm

## 许可证

[添加许可证信息]
