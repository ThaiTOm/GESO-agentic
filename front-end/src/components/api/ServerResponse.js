import React from 'react';
import ReactMarkdown from 'react-markdown';
import Plot from 'react-plotly.js';
import './ServerResponse.css'; // Make sure to create and style this CSS file

const ServerResponse = ({ response }) => {
    if (!response) return null;

    const isPlotlyFigure = (data) => data && typeof data === 'object' && 'data' in data && 'layout' in data;

    // Case 1: Data Analysis Response (Unchanged)
    if (response.text_summary_for_llm && response.plots_for_client) {
        const { text_summary_for_llm, plots_for_client } = response;
        return (
            <div className="response-container analysis-response">
                <div className="markdown-summary">
                    <ReactMarkdown>{text_summary_for_llm}</ReactMarkdown>
                </div>
                <div className="plots-grid">
                    {Object.entries(plots_for_client).map(([segment, plotData]) => {
                        if (!isPlotlyFigure(plotData)) return null;
                        return (
                            <div key={segment} className="plot-card">
                                <Plot
                                    data={plotData.data}
                                    layout={{ ...plotData.layout, autosize: true, title: segment }}
                                    useResizeHandler={true}
                                    style={{ width: '100%', height: '100%' }}
                                />
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }

    // Case 2: RAG Response (Improved UI)
    if (response.answer && Array.isArray(response.sources)) {
        const { answer, sources } = response;

        // Deduplicate sources based on document_id for a cleaner list
        const uniqueSources = sources.filter(
            (source, index, self) =>
                index === self.findIndex((s) => s.document_id === source.document_id)
        );

        return (
            <div className="response-container rag-response">
                <div className="rag-card">
                    <div className="markdown-answer">
                        <ReactMarkdown>{answer}</ReactMarkdown>
                    </div>
                    {uniqueSources.length > 0 && (
                        <div className="sources-section">
                            <h4 className="sources-title">Sources</h4>
                            <div className="sources-list">
                                {uniqueSources.map((source, index) => (
                                    <div key={source.document_id || index} className="source-tag">
                                        <span>{source.file_name}</span>
                                        <span className="source-score">Score: {source.score.toFixed(2)}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Case 3: Simple string response (Unchanged)
    const replyText = typeof response === 'object' ? JSON.stringify(response, null, 2) : response.toString();
    return (
        <div className="response-container simple-response">
            <p>{replyText}</p>
        </div>
    );
};

export default ServerResponse;