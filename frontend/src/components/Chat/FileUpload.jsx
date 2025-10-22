import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Paperclip, X, FileText, Upload, CheckCircle, AlertCircle } from 'lucide-react';
import { chatAPI } from '../../services/api';
import toast from 'react-hot-toast';

const FileUpload = ({ sessionId, onDocumentUploaded }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedDocs, setUploadedDocs] = useState([]);

  // Clear docs when session changes
  React.useEffect(() => {
    setUploadedDocs([]);
    console.log('FileUpload session changed to:', sessionId);
  }, [sessionId]);
  const fileInputRef = useRef(null);

  const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File too large. Maximum size is 10MB.');
      return;
    }

    // Validate file type
    const allowedTypes = ['pdf', 'docx', 'doc', 'txt'];
    const fileExt = file.name.toLowerCase().split('.').pop();
    
    if (!allowedTypes.includes(fileExt)) {
      toast.error('Unsupported file type. Use PDF, DOCX, DOC, or TXT files.');
      return;
    }

    await uploadFile(file);
  };

  const uploadFile = async (file) => {
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_id', sessionId);

      const result = await chatAPI.uploadChatDocument(sessionId, formData);
      
      const newDoc = {
        doc_id: result.doc_id,
        filename: result.filename,
        chunks_count: result.chunks_count,
        word_count: result.word_count,
        status: 'ready'
      };

      setUploadedDocs(prev => [...prev, newDoc]);
      onDocumentUploaded?.(newDoc);
      
      toast.success(`${file.name} uploaded and processed!`);
      
    } catch (error) {
      console.error('Upload error:', error);
      toast.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const removeDocument = async (docId) => {
    try {
      await chatAPI.removeChatDocument(sessionId, docId);
      setUploadedDocs(prev => prev.filter(doc => doc.doc_id !== docId));
      toast.success('Document removed');
    } catch (error) {
      toast.error('Failed to remove document');
    }
  };

  return (
    <div className="flex items-center space-x-2">
      {/* Upload Button */}
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
        className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
        title="Upload document for this conversation"
      >
        {isUploading ? (
          <Upload className="w-5 h-5 animate-pulse" />
        ) : (
          <Paperclip className="w-5 h-5" />
        )}
      </button>

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.doc,.txt"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Uploaded Documents Indicator */}
      <AnimatePresence>
        {uploadedDocs.length > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="flex items-center space-x-1"
          >
            <div className="flex items-center space-x-1 bg-blue-50 text-blue-700 px-2 py-1 rounded-full text-xs">
              <FileText className="w-3 h-3" />
              <span>{uploadedDocs.length} doc{uploadedDocs.length > 1 ? 's' : ''}</span>
            </div>
            
            {/* Remove All Button */}
            <button
              onClick={() => {
                uploadedDocs.forEach(doc => removeDocument(doc.doc_id));
              }}
              className="p-1 hover:bg-red-50 text-red-500 rounded"
              title="Remove all documents"
            >
              <X className="w-4 h-4" />
            </button>
            
            {/* Document List Dropdown */}
            <div className="relative group">
              <button className="p-1 hover:bg-gray-100 rounded">
                <CheckCircle className="w-4 h-4 text-green-500" />
              </button>
              
              {/* Tooltip with document list */}
              <div className="absolute bottom-full left-0 mb-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-50 pointer-events-none group-hover:pointer-events-auto">
                <div className="p-3">
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Uploaded Documents</h4>
                  <div className="space-y-2">
                    {uploadedDocs.map((doc) => (
                      <div key={doc.doc_id} className="flex items-center justify-between text-xs">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-gray-900 truncate">{doc.filename}</div>
                          <div className="text-gray-500">{doc.word_count} words, {doc.chunks_count} chunks</div>
                        </div>
                        <button
                          onClick={() => removeDocument(doc.doc_id)}
                          className="ml-2 p-1 hover:bg-red-50 text-red-500 rounded"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default FileUpload;