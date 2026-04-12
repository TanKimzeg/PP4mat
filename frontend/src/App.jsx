import React, { useState, useRef, useCallback, useEffect } from "react";
import ReactMarkdown from "react-markdown";

const API_BASE = import.meta.env.VITE_API_BASE || "";

function App() {
    const [file, setFile] = useState(null);
    const [result, setResult] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [fixing, setFixing] = useState(false);
    const [error, setError] = useState(null);
    const [stats, setStats] = useState({ total_checks: 0, total_fixes: 0 });
    const [fixedInfo, setFixedInfo] = useState(null);
    const [hasChecked, setHasChecked] = useState(false);
    const dropRef = useRef(null);

    const resetState = () => {
        setResult(null);
        setError(null);
        setFixedInfo(null);
        setHasChecked(false);
    };

    const refreshStats = useCallback(async () => {
        try {
            const r = await fetch(`${API_BASE}/stats/`);
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const data = await r.json();
            setStats({
                total_checks: Number(data?.total_checks ?? 0),
                total_fixes: Number(data?.total_fixes ?? 0),
                updated_at: data?.updated_at ?? null,
            });
        } catch {
            // 请求失败时保持已有值（至少是 0）
            setStats((s) => s ?? { total_checks: 0, total_fixes: 0 });
        }
    }, []);

    useEffect(() => {
        refreshStats();
    }, [refreshStats]);

    const handleFile = (f) => {
        if (!f) return;
        if (!f.name.toLowerCase().endsWith(".docx")) {
            setError("仅支持 .docx 文件");
            return;
        }
        setFile(f);
        resetState();
    };

    const handleFileChange = (e) => handleFile(e.target.files[0]);

    const handleDragOver = (e) => {
        e.preventDefault();
        dropRef.current?.classList.add("dragover");
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        dropRef.current?.classList.remove("dragover");
    };

    const handleDrop = (e) => {
        e.preventDefault();
        dropRef.current?.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
            e.dataTransfer.clearData();
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file) { setError("请先选择文件"); return; }
        setUploading(true);
        setError(null);
        setResult(null);
        setFixedInfo(null);

        const formData = new FormData();
        formData.append("file", file);
        try {
            const response = await fetch(`${API_BASE}/upload/`, { method: "POST", body: formData });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            setResult(data);
            setHasChecked(true);
            if (data?.stats) setStats(data.stats);
            else refreshStats();
        } catch (err) {
            setError(`上传失败: ${err.message}`);
        } finally {
            setUploading(false);
        }
    };

    const handleAutoFix = async () => {
        if (!file) { setError("请先选择文件"); return; }
        setFixing(true);
        setError(null);
        setFixedInfo(null);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch(`${API_BASE}/fix/`, { method: "POST", body: formData });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            setFixedInfo(data);
            if (data?.stats) setStats(data.stats);
            else refreshStats();
        } catch (err) {
            setError(`自动修复失败: ${err.message}`);
        } finally {
            setFixing(false);
        }
    };

    const pickFile = useCallback(() => {
        const input = document.getElementById("file-input-hidden");
        input && input.click();
    }, []);

    return (
        <div className="main-wrapper">
            <div className="card">
                <h1 className="tool-title">本科毕业论文格式检测</h1>

                <form onSubmit={handleSubmit}>
                    <div
                        ref={dropRef}
                        className="upload-area"
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                    >
                        <p style={{margin:"0 0 .4rem"}}>{file ? `已选择：${file.name}` : "拖拽或点击选择 .docx 文件"}</p>
                        <small style={{marginTop: "-0.4rem"}}>
                            识别结果仅供参考，请以学校提供的论文模板与最新规范为准。
                        </small>
                        <input id="file-input-hidden" type="file" onChange={handleFileChange} accept=".docx" />

                        <div className="btn-row">
                            <button type="button" className="custom-file-btn" onClick={pickFile}>选择文件</button>
                            <button type="submit" className="submit-btn" disabled={!file || uploading}>{uploading ? "检测中..." : "上传并检测"}</button>
                            {hasChecked && (
                                <button type="button" className="fix-btn" onClick={handleAutoFix} disabled={!file || fixing}>{fixing ? "修复中..." : "自动修复并下载"}</button>
                            )}
                        </div>
                    </div>
                </form>

                {error && <div className="result-panel" style={{borderColor:'#fca5a5', background:'#fff1f2'}}><h2>错误</h2><p style={{color:'#b91c1c'}}>{error}</p></div>}

                {fixedInfo && (
                    <div className="result-panel">
                        <h2>自动修复</h2>
                        <p style={{marginTop: 0}}>{fixedInfo.message}</p>
                        {fixedInfo.fixed_filename && (
                            <a className="download-link" href={`${API_BASE}/download/fixed/${fixedInfo.fixed_filename}`}>下载修复后的 Word 文件</a>
                        )}
                    </div>
                )}

                {result && (
                    <div className="result-panel">
                        <div className="markdown-body">
                            <ReactMarkdown>{result.report || result.message}</ReactMarkdown>
                        </div>
                    </div>
                )}

                <footer>
                    <div>© {new Date().getFullYear()} PPSUC · Paper4mat</div>
                    <div className="footer-stats">
                        <span>累计检测次数：{stats?.total_checks ?? 0}</span>
                        <span className="dot">·</span>
                        <span>累计自动修复次数：{stats?.total_fixes ?? 0}</span>
                    </div>
                </footer>
            </div>
        </div>
    );
}

export default App;
