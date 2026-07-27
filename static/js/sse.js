/**
 * 千卷 QianJuan — SSE 流式接收器
 *
 * Usage:
 *   startGeneration('/api/generate/settings/xxx', {}, outputEl, statusEl)
 */

let currentController = null;

async function startGeneration(url, body, outputEl, statusEl, onComplete) {
    if (currentController) {
        currentController.abort();
    }
    currentController = new AbortController();

    outputEl.textContent = '';
    if (statusEl) statusEl.textContent = '生成中...';

    let fullContent = '';

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: currentController.signal,
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: '未知错误' }));
            throw new Error(err.detail || `HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') {
                        if (statusEl) statusEl.textContent = '生成完成';
                        if (onComplete) onComplete(fullContent);
                        currentController = null;
                        return;
                    }
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.type === 'chunk') {
                            fullContent += parsed.content;
                            outputEl.textContent = fullContent;
                            outputEl.scrollTop = outputEl.scrollHeight;
                        } else if (parsed.type === 'error') {
                            throw new Error(parsed.message);
                        } else if (parsed.type === 'result') {
                            fullContent = parsed.content;
                            outputEl.textContent = fullContent;
                            if (statusEl) statusEl.textContent = '生成完成';
                            if (onComplete) onComplete(fullContent);
                            currentController = null;
                            return;
                        }
                    } catch (e) {
                        if (e.message && !e.message.startsWith('Unexpected')) {
                            throw e;
                        }
                        fullContent += data;
                        outputEl.textContent = fullContent;
                    }
                }
            }
        }

        if (statusEl) statusEl.textContent = '生成完成';
        if (onComplete) onComplete(fullContent);
    } catch (err) {
        if (err.name === 'AbortError') {
            if (statusEl) statusEl.textContent = '已取消';
        } else {
            if (statusEl) statusEl.textContent = '生成失败: ' + err.message;
            outputEl.textContent += '\n\n❌ 错误: ' + err.message;
        }
    } finally {
        currentController = null;
    }
}

function cancelGeneration() {
    if (currentController) {
        currentController.abort();
        currentController = null;
    }
}
