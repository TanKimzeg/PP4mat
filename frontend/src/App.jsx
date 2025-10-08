import React, { useState, useRef, useCallback } from "react";
import ReactMarkdown from "react-markdown";

function App() {
    const [file, setFile] = useState(null);
    const [result, setResult] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState(null);
    const dropRef = useRef(null);

    const resetState = () => {
        setResult(null);
        setError(null);
    };

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
        const formData = new FormData();
        formData.append("file", file);
        try {
            const response = await fetch("/upload/", { method: "POST", body: formData });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            setResult(data);
        } catch (err) {
            setError(`上传失败: ${err.message}`);
        } finally {
            setUploading(false);
        }
    };

    const pickFile = useCallback(() => {
        const input = document.getElementById("file-input-hidden");
        input && input.click();
    }, []);

    return (
        <div className="main-wrapper">
            <div className="card">
                <h1 className="tool-title">论文格式检测工具</h1>
                <form onSubmit={handleSubmit}>
                    <div
                        ref={dropRef}
                        className="upload-area"
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                    >
                        <p style={{margin:"0 0 .4rem"}}>{file ? `已选择：${file.name}` : "拖拽或点击选择 .docx 文件"}</p>
                        <small>支持单文件，自动进行格式规则检测</small>
                        <input id="file-input-hidden" type="file" onChange={handleFileChange} accept=".docx" />
                        <button type="button" className="custom-file-btn" onClick={pickFile}>选择文件</button>
                        <button type="submit" className="submit-btn" disabled={!file || uploading}>{uploading ? "上传中..." : "上传并检测"}</button>
                    </div>
                </form>
                {error && <div className="result-panel" style={{borderColor:'#fca5a5', background:'#fff1f2'}}><h2>错误</h2><p style={{color:'#b91c1c'}}>{error}</p></div>}
                {result && (
                    <div className="result-panel">
                        <div className="markdown-body">
                            <ReactMarkdown>{result.report || result.message}</ReactMarkdown>
                        </div>
                    </div>
                )}
                <footer>© {new Date().getFullYear()} Paper4mat</footer>
            </div>
        </div>
    );
}

export default App;
