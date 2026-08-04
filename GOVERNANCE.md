# 治理说明

## 概述

全栈 AI 代理模板由 [Vstorm](https://vstorm.co) 维护，这是一家位于波兰的 AI 工程咨询公司。

## 决策机制

本项目采用**仁慈独裁者**治理模型：

- **项目负责人**：Kacper Wlodarczyk（[@sebastiondev](https://github.com/sebastiondev)）对项目方向、功能包含和发布做出最终决定。
- **社区意见**：功能请求、Bug 报告和讨论通过 [GitHub Issues](https://github.com/vstorm-co/framework-agent-python/issues) 和 Pull Request 进行。所有意见都会被考虑。
- **Pull Request**：由项目负责人或指定的维护者审查。所有 PR 在合并前至少需要一人批准。

## 角色与职责

### 项目负责人

**现任**：Kacper Wlodarczyk（[@sebastiondev](https://github.com/sebastiondev)）

- 制定项目路线图和长期方向
- 批准或拒绝新功能和架构变更
- 发布版本并发布到 PyPI
- 响应安全漏洞报告（详见 [SECURITY.md](SECURITY.md)）
- 授予或撤销维护者权限
- 对合并决策拥有最终决定权

### 维护者

**现任**：Vstorm 团队

- 审查和合并 Pull Request（至少需要一人批准）
- 分类问题：标记、分配、关闭重复项
- 确保合并前 CI 通过
- 保持文档准确性
- 监控并回应社区讨论

### 贡献者

**现任**：任何人（需 [DCO](DCO) 签署）

- 提交包含 Bug 修复、功能或文档改进的 Pull Request
- 通过 GitHub Issues 报告 Bug 和请求功能
- 参与讨论和代码审查
- 遵循项目的编码标准和测试要求

## 贡献

所有贡献都需要[开发者原创证书（DCO）](DCO)签署。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 发布

发布遵循[语义化版本控制](https://semver.org/)。项目负责人决定发布时间和内容。

## 人员风险与连续性计划

项目保持**人员风险系数为 2**。至少有两人拥有管理项目每个关键方面（GitHub 组织所有权、PyPI 发布、DNS、CI/CD 密钥）所需的访问权限和知识。

如果任何单个贡献者无法继续工作，项目设计为能以最小的中断继续运行：

- **GitHub 组织**：仓库归 [vstorm-co](https://github.com/vstorm-co) GitHub 组织所有。多名团队成员拥有**所有者**权限，确保仓库管理、问题分类和 PR 合并不存在单点故障。
- **PyPI**：PyPI 上的 `framework-agent-python` 包有多名具有发布权限的维护者，可独立继续发布。
- **DNS/域名**：`vstorm.co` 域名在组织下注册，而非个人账户。
- **CI/CD**：GitHub Actions 密钥在组织级别管理。任何组织所有者均可更新或轮换它们。
- **Fork**：作为 MIT 许可的项目，社区可随时 Fork 并继续开发，无法律障碍。

如果项目负责人永久无法履职，剩余的组织所有者将在一周内任命新的负责人。

## 安全

安全漏洞应按照 [SECURITY.md](SECURITY.md) 报告。关键问题优先于所有其他工作。
