
#!/bin/bash
# 清理storage超过2天的临时文件夹以及文件
find storage/temp -mindepth 1 -mtime +2 -exec rm -rf {} \;