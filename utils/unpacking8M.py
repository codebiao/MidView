import struct
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import sys
import io
import matplotlib.patches as patches

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def parser_8M(file_path):
    """
    解析固定 8MB 格式的二进制图像文件
    """
    file_size = 8388608 # 8MB = 8388608 Bytes
    
    with open(file_path, 'rb') as f:
        content = f.read()
        
    if len(content) != file_size:
        raise ValueError(f"文件大小异常: 当前为 {len(content)} 字节，预期应为 {file_size} 字节。")

    # ==========================
    # 1. 解析 Head (前 64 字节)
    # ==========================
    # 使用小端序 '<' 解析：6个 uint32 ('6I') 和 40 字节字符 ('40s')
    head_data = content[:64]
    head_unpacked = struct.unpack('<6I40s', head_data)
    
    head = {
        'packet_id': head_unpacked[0],
        'version': head_unpacked[1],
        'nimc_num': head_unpacked[2],
        'sensor_mono': head_unpacked[3],
        'sensor_width': head_unpacked[4],
        'sensor_height': head_unpacked[5],
        'reserve2': head_unpacked[6]
    }

    # ==========================
    # 2. 解析 Footer (后 8 字节)
    # ==========================
    # 读取最后的 8 字节作为一个 uint64 ('<Q')
    footer_data = content[-8:]
    footer_val = struct.unpack('<Q', footer_data)[0]

    # C/C++ 位段 (bitfield) 在小端序机器上通常从低位到高位排列
    # 提取位信息并使用掩码 (mask) 进行隔离
    footer = {
        'check_sum': footer_val & 0xFFFFFF,                    # 第 0-23 位 (24位)
        'valid_line': (footer_val >> 24) & 0x7FFFFF,           # 第 24-46 位 (23位)
        'cr_flag': (footer_val >> 47) & 0x1,                   # 第 47 位 (1位)
        'packet_end': (footer_val >> 48) & 0xFFFF              # 第 48-63 位 (16位)
    }

    # ==========================
    # 3. 解析 Data (中间部分)
    # ==========================
    sensor_width = head['sensor_width']
    valid_line = footer['valid_line']
    
    # 每行实际的总字节数: 像素数 * 2 + 后缀 8 字节
    line_bytes = sensor_width * 2 + 8 
    
    # 有效数据段长度 = 行数 * 每行的字节数
    data_offset = 64
    valid_data_length = valid_line * line_bytes
    
    # 提取出实际包含数据的二进制切片
    raw_valid_data = content[data_offset : data_offset + valid_data_length]
    
    # 将一维数据用 numpy 转化为 二维矩阵 (行数 x 每行字节数)，数据类型先设为 uint8
    raw_array = np.frombuffer(raw_valid_data, dtype=np.uint8).reshape(valid_line, line_bytes)
    
    # 切片截取图像数据：去掉每行最后的 8 字节，保留前面的 (sensor_width * 2) 字节
    image_bytes = raw_array[:, :sensor_width * 2]
    
    # 由于进行过列切片，numpy 的内存可能变得不连续。在通过 view 转换数据类型前，需确保内存连续
    image_bytes_contiguous = np.ascontiguousarray(image_bytes)
    
    # 2个 uint8 字节构成 1个像素，将数据视图转换为 uint16
    # (如果图像颜色不对，可能是大小端问题，可以将 '<u2' 改为 '>u2')
    data = image_bytes_contiguous.view(dtype='<u2')

    return head, data, footer