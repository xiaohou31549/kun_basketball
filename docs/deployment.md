# NBA 比赛视频下载器 - Docker 部署指南

## 开发流程

1. 本地开发和测试
   ```bash
   # 构建测试镜像
   docker build -t nba-downloader:test .
   
   # 运行测试
   docker run -v $(pwd)/config.py:/app/config.py -v $(pwd)/video:/downloads nba-downloader:test
   ```

2. 发布新版本
   ```bash
   # 给代码打标签
   git tag v1.0.0
   git push origin v1.0.0
   ```
   
   GitHub Action 会自动构建镜像并推送到 Docker Hub。

## 群晖部署步骤

1. 在群晖上安装 Docker
   - 通过群晖套件中心安装 Docker
   - 通过套件中心安装 Container Manager（如果可用）

2. 创建部署目录
   ```bash
   # 在群晖上创建目录
   mkdir -p /volume1/docker/nba-downloader
   ```

3. 上传配置文件
   - 只需要上传两个文件到群晖：
     - `docker-compose.yml`
     - `config.py`
   - 修改 `docker-compose.yml` 中的镜像名称为你的 Docker Hub 用户名
   - 修改 `config.py` 中的下载路径等配置

4. 拉取镜像和启动容器
   ```bash
   # SSH 登录到群晖
   ssh admin@nas_ip
   
   # 进入项目目录
   cd /volume1/docker/nba-downloader
   
   # 拉取最新镜像并启动
   docker-compose pull
   docker-compose up -d
   ```

5. 查看日志
   ```bash
   docker logs nba-downloader
   ```

## 更新程序

当有新版本发布时，只需要：

1. 拉取新镜像
   ```bash
   docker-compose pull
   ```

2. 重启容器
   ```bash
   docker-compose up -d
   ```

## 优势

1. **简化部署**
   - 不需要在群晖上构建镜像
   - 不需要复制源代码文件
   - 只需要管理配置文件

2. **版本控制**
   - 每个版本都有对应的 Docker 镜像
   - 可以方便地回滚到之前的版本
   - GitHub 自动构建保证代码和镜像的一致性

3. **配置管理**
   - 配置文件与代码分离
   - 可以针对不同环境使用不同配置
   - 更新程序时不会覆盖配置

4. **维护方便**
   - 本地开发和测试
   - 自动化的构建和发布流程
   - 集中化的版本管理

## 注意事项

1. 确保 Docker Hub 账号和密码配置正确
2. 定期清理旧的 Docker 镜像以节省空间
3. 建议在 config.py 中使用环境变量来配置敏感信息
4. 记得备份配置文件
