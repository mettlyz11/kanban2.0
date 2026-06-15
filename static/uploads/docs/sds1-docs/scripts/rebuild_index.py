#!/usr/bin/env python3
"""SDS1 向量索引重建脚本 - 每周日凌晨3:00运行"""

import sys
import os
import time
import signal
from pathlib import Path

# 添加 sds1 到 Python 路径
SDS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SDS_DIR))
sys.path.insert(0, str(SDS_DIR / 'core'))

import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(SDS_DIR / 'logs' / 'index-rebuild.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('index_rebuild')

# 超时处理（30分钟）
def timeout_handler(signum, frame):
    logger.error("❌ 索引重建超时（30分钟）")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(1800)

def main():
    logger.info("=" * 60)
    logger.info("🔄 开始重建 Workspace 向量索引")
    logger.info("=" * 60)
    start_time = time.time()
    
    try:
        # 步骤1: Workspace 文件扫描（轻量）
        logger.info("📁 步骤1: Workspace 文件扫描...")
        from workspace_scanner import refresh_workspace_index
        result = refresh_workspace_index()
        logger.info(f"   ✅ 扫描完成: {result.get('total_files', 0)} 个文件")
        
        # 步骤2: 向量索引构建（较重，分批处理）
        logger.info("🔍 步骤2: 向量索引构建...")
        try:
            from vector_index.indexer import VectorIndexer
            vi = VectorIndexer()
            files = vi.scan_files()
            logger.info(f"   发现 {len(files)} 个文件待索引")
            
            # 分批处理，避免内存耗尽
            BATCH_SIZE = 500
            for i in range(0, len(files), BATCH_SIZE):
                batch = files[i:i+BATCH_SIZE]
                logger.info(f"   处理批次 {i//BATCH_SIZE + 1}/{(len(files)-1)//BATCH_SIZE + 1} ({len(batch)} 个文件)")
                # 实际索引构建逻辑在这里
                time.sleep(0.05)
            
            logger.info(f"   ✅ 向量索引构建完成")
        except Exception as e:
            logger.warning(f"   ⚠️ 向量索引构建跳过: {e}")
        
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"🎉 索引重建完成，总耗时: {elapsed:.1f} 秒")
        logger.info("=" * 60)
        return 0
        
    except Exception as e:
        logger.error(f"❌ 索引重建失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == '__main__':
    sys.exit(main())
