# 自定义干扰库使用指南

本指南说明如何准备和使用自定义干扰库。

## 功能说明

程序支持用户上传自己的干扰库文件或文件夹，用于MRM转换优化计算。上传的干扰库会自动进行格式验证，确保包含所有必需的列。

## 干扰库格式要求

### NIST方法干扰库

**必需列：**
- `InChIKey`: 化合物的InChIKey标识符
- `PrecursorMZ`: 母离子m/z值
- `RT`: 保留时间（分钟）
- `MSMS`: 碎片离子m/z值
- `NCE`: 归一化碰撞能
- `CE`: 碰撞能
- `Ion_mode`: 离子模式（如 'P' 表示正离子模式）
- `Precursor_type`: 母离子类型（如 '[M+H]+'）

**示例CSV格式：**
```csv
InChIKey,PrecursorMZ,RT,MSMS,NCE,CE,Ion_mode,Precursor_type
YASYVMFAVPKPKE-UHFFFAOYSA-N,202.0433,10.5,175.0320,30.0,30.0,P,[M+H]+
```

### QE方法干扰库

**必需列：**
- `Alignment ID`: 对齐ID
- `Average Mz`: 平均m/z值
- `Average Rt(min)`: 平均保留时间（分钟）
- `CE`: 碰撞能
- `MS/MS spectrum`: MS/MS谱图字符串（格式：mz1:intensity1 mz2:intensity2 ...）

**示例CSV格式：**
```csv
Alignment ID,Average Mz,Average Rt(min),CE,MS/MS spectrum
ID001,202.0433,10.5,30.0,175.0320:1000 131.0600:500
```

## 使用方法

### 1. 准备干扰库文件

确保您的干扰库文件或文件夹包含所有必需的列，并保存为CSV格式。

### 2. 使用命令行参数

```bash
# 使用单个CSV文件作为干扰库
python main.py --intf-db nist --custom-intf-db /path/to/your/interference_db.csv

# 使用包含多个CSV文件的文件夹作为干扰库
python main.py --intf-db nist --custom-intf-db /path/to/your/interference_db_folder

# 使用相对路径
python main.py --intf-db nist --custom-intf-db ./my_interference_db.csv
```

### 3. 验证过程

程序会自动验证干扰库格式：
- 检查路径是否存在
- 检查文件格式（必须是CSV）
- 检查是否包含所有必需的列
- 显示干扰库基本信息（文件数、行数等）

如果验证失败，程序会显示详细的错误信息，帮助您修正格式。

### 4. 跳过验证（不推荐）

仅在确认干扰库格式完全正确时，可以使用 `--skip-validation` 跳过验证：

```bash
python main.py --intf-db nist --custom-intf-db /path/to/db --skip-validation
```

## 注意事项

1. **文件编码**：确保CSV文件使用UTF-8编码
2. **列名大小写**：列名必须与要求完全匹配（包括大小写）
3. **数据类型**：数值列（如PrecursorMZ、RT等）应为数字类型
4. **文件大小**：大文件会被分块读取，不会一次性加载到内存
5. **文件夹结构**：如果使用文件夹，所有CSV文件应具有相同的列结构

## 示例

### 示例1：使用单个文件

```bash
python main.py \
    --intf-db nist \
    --custom-intf-db ./my_custom_interference.csv \
    --max-compounds 100 \
    --output results_with_custom_db.csv
```

### 示例2：使用文件夹

```bash
python main.py \
    --intf-db nist \
    --custom-intf-db ./interference_databases/my_db_folder \
    --max-compounds 50
```

### 示例3：QE方法自定义干扰库

```bash
python main.py \
    --intf-db qe \
    --custom-intf-db ./qe_interference_db.csv \
    --single-compound \
    --inchikey "YOUR_INCHIKEY"
```

## 故障排除

### 错误：干扰库路径不存在
- 检查路径是否正确
- 使用绝对路径或确保相对路径正确

### 错误：缺少必需的列
- 检查CSV文件是否包含所有必需的列
- 确保列名拼写正确（包括大小写）

### 错误：文件格式不正确
- 确保文件是CSV格式
- 检查文件编码是否为UTF-8

### 性能问题
- 大文件会被自动分块处理
- 如果文件夹包含大量文件，首次运行可能需要较长时间建立索引

## 技术支持

如有问题，请检查：
1. 干扰库格式是否符合要求
2. 文件路径是否正确
3. 文件编码是否为UTF-8
4. 查看日志输出的详细错误信息
