---
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*), Bash(git push:*)
description: Create a git commit
---

## 上下文

- 当前git状态: !`git status`
- 当前git差异(已暂存和未暂存的变化): !`git diff HEAD`
- 当前分支: !`git branch --show-current`
- 最近提交: !`git log --oneline -10`

## Your task

基于上述上下文，创建一个git commit, 并且推送到远程仓库。