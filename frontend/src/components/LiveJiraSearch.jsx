import { Loader2, Search } from 'lucide-react';
import { useState } from 'react';
import { jiraAPI } from '../services/api';

const LiveJiraSearch = () => {
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [results, setResults] = useState(null);

    const runSearch = async () => {
        if (!query.trim()) return;
        setLoading(true); setError(null);
        try {
            const data = await jiraAPI.liveSearch(query.trim());
            setResults(data);
        } catch (e) {
            setError(e.message || 'Search failed');
        } finally { setLoading(false); }
    };

    const onKeyDown = (e) => { if (e.key === 'Enter') runSearch(); };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold mb-4 dark:text-white flex items-center"><Search className="w-5 h-5 mr-2 text-blue-600" />Live JIRA Search</h2>
            <div className="flex space-x-2 mb-4">
                <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={onKeyDown}
                    placeholder="Ticket key (e.g. MBSL3-123) or text..."
                    className="flex-1 px-3 py-2 border rounded-md dark:bg-gray-700 dark:text-white dark:border-gray-600"
                />
                <button onClick={runSearch} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50" disabled={loading}>Search</button>
            </div>
            {loading && <div className="flex items-center text-sm text-gray-500 dark:text-gray-400"><Loader2 className="w-4 h-4 animate-spin mr-2" />Searching...</div>}
            {error && <div className="text-sm text-red-600 mb-3">{error}</div>}
            {results && (
                <div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">JQL: {results.jql} | {results.count} issues</div>
                    <div className="max-h-80 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-md divide-y dark:divide-gray-700">
                        {results.issues.map(issue => (
                            <div key={issue.key} className="p-3 text-sm flex justify-between items-start hover:bg-gray-50 dark:hover:bg-gray-700">
                                <div className="pr-4">
                                    <div className="font-medium text-blue-600 dark:text-blue-400">{issue.key}</div>
                                    <div className="text-gray-700 dark:text-gray-300 truncate max-w-xl">{issue.summary}</div>
                                    <div className="text-xs text-gray-500 dark:text-gray-400 space-x-2 mt-1">
                                        <span>{issue.status}</span>
                                        {issue.priority && <span>{issue.priority}</span>}
                                        <span>{issue.assignee || 'Unassigned'}</span>
                                    </div>
                                </div>
                                <div className="text-xs text-gray-400 dark:text-gray-500 text-right">
                                    <div>{new Date(issue.updated).toLocaleDateString()}</div>
                                    <div>{issue.issueType}</div>
                                </div>
                            </div>
                        ))}
                        {results.issues.length === 0 && <div className="p-3 text-sm text-gray-500 dark:text-gray-400">No issues found.</div>}
                    </div>
                </div>
            )}
        </div>
    );
};

export default LiveJiraSearch;
