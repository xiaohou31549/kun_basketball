#!/usr/bin/env python3
import os
from datetime import datetime, timedelta
import argparse
import re
import shutil

def get_sort_prefix(date_str):
    # 从日期字符串中提取月份和日期
    match = re.match(r'(\d+)月(\d+)号', date_str)
    if not match:
        return "0000"  # 默认前缀
    
    month = int(match.group(1))
    day = int(match.group(2))
    
    # 使用9999减去月份和日期的值，确保最近的日期有更大的数字
    # 格式化为4位数，确保排序正确
    prefix = 9999 - (month * 31 + day)  # 用31天作为每月的基数
    return f"{prefix:04d}"

def cleanup_old_directories(root_dir, max_dirs=50):
    """清理旧的目录，保持总数不超过最大限制"""
    # 获取所有目录
    dirs = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
    
    # 如果目录数量未超过限制，无需清理
    if len(dirs) <= max_dirs:
        return
    
    # 按照排序前缀排序（较大的前缀代表较早的日期）
    dirs.sort(key=lambda x: x.split('_')[0] if x.split('_')[0].isdigit() else "0000", reverse=True)
    
    # 需要删除的目录数量
    dirs_to_remove = len(dirs) - max_dirs
    
    # 删除前缀最大的几个目录（最早的比赛）
    for dir_to_remove in dirs[:dirs_to_remove]:
        dir_path = os.path.join(root_dir, dir_to_remove)
        try:
            shutil.rmtree(dir_path)
            print(f"\n已删除旧目录: {dir_to_remove}")
        except Exception as e:
            print(f"\n删除目录失败 {dir_to_remove}: {str(e)}")

def rename_game_directories(debug_mode=False):
    # 获取前一天的日期，格式化为"X月X号"的形式
    yesterday = datetime.now() - timedelta(days=1)
    date_str = f"{yesterday.month}月{yesterday.day}号"
    
    # 获取项目根目录
    root_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"\n当前工作目录: {root_dir}")
    print(f"处理日期: {date_str}")
    
    # 遍历根目录下的所有目录
    subdirs = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
    
    if not subdirs:
        print("没有找到任何子目录！")
        return
        
    print(f"\n找到 {len(subdirs)} 个子目录:")
    for d in subdirs:
        print(f"- {d}")
    
    # 编译正则表达式用于匹配比赛目录格式（X月X号比赛信息）
    dir_pattern = re.compile(r'^(?:\d{4}_)?(\d+月\d+号)(.+)$')
    
    processed = False
    # 遍历根目录下的所有目录
    for dirname in subdirs:
        match = dir_pattern.match(dirname)
        if match:
            # 如果已经有排序前缀，先去掉它
            date_part = match.group(1)  # 日期部分
            game_part = match.group(2)  # 比赛信息部分
            
            # 判断是否处理该目录
            if debug_mode or date_part == date_str:
                # 获取排序前缀
                sort_prefix = get_sort_prefix(date_part)
                
                # 创建新的目录名（添加排序前缀，并在日期和比赛信息之间添加下划线）
                new_dirname = f"{sort_prefix}_{date_part}_{game_part}"
                
                if new_dirname != dirname:  # 只在需要修改时进行重命名
                    old_path = os.path.join(root_dir, dirname)
                    new_path = os.path.join(root_dir, new_dirname)
                    
                    # 重命名目录
                    try:
                        os.rename(old_path, new_path)
                        print(f"\n成功重命名: {dirname} -> {new_dirname}")
                        processed = True
                    except Exception as e:
                        print(f"\n重命名失败 {dirname}: {str(e)}")
                else:
                    print(f"\n目录 '{dirname}' 已经是正确格式")
            else:
                print(f"\n跳过目录 '{dirname}' （不是昨天的比赛目录）")
        else:
            print(f"\n跳过目录 '{dirname}' （不符合比赛目录命名格式）")
    
    if not processed:
        if debug_mode:
            print("\n没有找到需要重命名的目录")
        else:
            print(f"\n没有找到昨天（{date_str}）的比赛目录需要重命名")
    
    # 清理旧目录，保持总数不超过50个
    cleanup_old_directories(root_dir, max_dirs=50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='在比赛目录的日期和比赛信息之间添加下划线，并添加排序前缀')
    parser.add_argument('--debug', '-d', action='store_true', 
                      help='调试模式：处理所有比赛目录，不限制只处理当天的目录')
    args = parser.parse_args()
    
    rename_game_directories(debug_mode=args.debug)
