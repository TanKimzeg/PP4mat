import React, { useState } from "react";
import ReactMarkdown from "react-markdown";

function App() {
    const [file, setFile] = useState(null);
    const [result, setResult] = useState(null);

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file) {
            alert("请先选择文件！");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch("/upload/", {
                method: "POST",
                body: formData,
            });
            const data = await response.json();
            setResult(data);
        } catch (error) {
            console.error("上传失败：", error);
        }
    };

    return (
        <div>
            <h1>论文格式检测工具</h1>
            <form onSubmit={handleSubmit}>
                <input type="file" onChange={handleFileChange} accept=".docx" />
                <button type="submit">上传并检测</button>
            </form>
            {result && (
                <div>
                    <h2>检测结果</h2>
                    {
                        <ReactMarkdown>{result.report}</ReactMarkdown>
                    }
                </div>
            )}
        </div>
    );
}

export default App;
