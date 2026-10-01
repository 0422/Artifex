# 按端口清理残留的后端 / 前端进程。
#
# 背景：uvicorn --reload 会由 reloader（父进程）spawn 出真正监听端口的 server 子进程。
# 在 PyCharm 终端里按 Ctrl+C 常常只送到第一层，server 子进程就变成孤儿继续占用端口，
# 表现为"后端杀不死"、端口被占，甚至请求打到迁移前启动的旧进程上导致接口全部 500。
#
# 用法（在 backend 目录下）：
#   .\kill-backend.bat             杀占用 8000 的进程（默认后端）
#   .\kill-backend.bat 5173        杀占用 5173 的进程（前端）
#   .\kill-backend.bat 8000 5173   一次清理多个端口

# ValueFromRemainingArguments：cmd 经 .bat 透传进来的多个端口会全部落到这里，
# 否则 -File 模式下命名数组参数只会吃到第一个值
param([Parameter(ValueFromRemainingArguments = $true)][int[]]$Ports = @(8000))

$killed = 0

foreach ($port in $Ports) {
    $pids = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { $_.OwningProcess } | Where-Object { $_ } | Sort-Object -Unique)

    if (-not $pids) {
        Write-Host "[kill] 端口 $port 当前没有进程占用。"
        continue
    }

    foreach ($procId in $pids) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        $name = if ($proc) { $proc.ProcessName } else { "已退出" }
        Write-Host "[kill] 端口 $port 的监听者 PID $procId ($name)，结束进程树..."
        # /T 连子进程一起杀，/F 强制；正是这一步能清掉 uvicorn spawn 出来的孤儿 server
        & taskkill /PID $procId /T /F
        if ($LASTEXITCODE -eq 0) { $killed++ }
    }
}

if ($killed -gt 0) {
    Write-Host "[kill] 清理完成，共结束 $killed 个进程。"
} else {
    Write-Host "[kill] 没有需要结束的进程。"
}
