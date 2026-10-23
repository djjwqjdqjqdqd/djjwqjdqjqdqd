# TutuCloud Build

兔兔客户端的公开打包基础设施。这个仓库开源打包脚本；客户端源码保留在独立的私有仓库中。

## 使用

在 Actions 中打开 **Build TutuCloud from private source**，点击 **Run workflow**，选择平台与私有源码的分支、标签或提交。默认只打包 Windows，`all` 会打包全部平台。本仓库不自动监听推送或拉取请求。

完成后从该次运行的 Artifacts 下载 `tutu-windows` 等产物。Windows 同时提供 ZIP 与安装器，使用客户端源码中的软件渲染配置。只上传最终安装包，不上传源码目录或打包临时目录。每组产物附带版本、源码提交和 SHA-256 清单。

## Actions Secrets

仓库配置以下 Secrets，值不写入 Git：

| 名称 | 用途 |
| --- | --- |
| `SOURCE_REPOSITORY` | 私有源码仓库 |
| `SOURCE_SSH_KEY` | 仅对源码仓库有效的只读 SSH Deploy Key |
| `BUILD_LOG_KEY` | 32 字节随机密钥的 Base64，用于 AES-256-GCM 加密构建日志 |
| `XOR_KEY`、`OSS_URL_1` 至 `OSS_URL_5` | 客户端配置引导，沿用私有源码仓库的配置 |
| `PANEL_TYPE`、`API_PREFIX` | 面板类型及接口前缀；可选项沿用客户端默认行为 |
| `APP_NAME`、`APP_NAME_EN`、`PACKAGE_NAME` | 品牌与应用标识 |
| `ANDROID_KEYSTORE_BASE64`、`ANDROID_KEY_ALIAS`、`ANDROID_STORE_PASSWORD`、`ANDROID_KEY_PASSWORD` | 原有 Android 发布签名 |

私有源码的 checkout 不持久化凭据。第三方 Actions 固定到提交；不缓存私有构建输出，不给拉取请求开放打包 Secrets。

## 构建日志

公开日志只显示步骤结果；详细的编译输出进入 `encrypted-diagnostics-平台` 附件，以 AES-256-GCM 加密。维护者在本机设置 `BUILD_LOG_KEY` 后，可运行：

```sh
node scripts/decrypt-log.mjs step.enc local-build.log
```

解密后的日志仅用于本地排错，不要上传明文日志。Windows、Android、macOS、Linux 与 iOS 复用私有项目的打包命令；iOS 产物包含未签名构建使用的核心 framework，不提供自动签名发布。
