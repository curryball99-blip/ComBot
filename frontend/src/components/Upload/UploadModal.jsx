import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Upload, 
  FileText, 
  CheckCircle, 
  AlertCircle,
  Loader2,
  File
} from 'lucide-react';
import { chatAPI } from '../../services/api';
import useChatStore from '../../stores/chatStore';

const SUPPORTED_TYPES = {
  'application/pdf': { icon: FileText, label: 'PDF' },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { icon: FileText, label: 'DOCX' },
  'application/msword': { icon: FileText, label: 'DOC' },
  'text/plain': { icon: FileText, label: 'TXT' },
  'text/markdown': { icon: FileText, label: 'MD' },
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': { icon: File, label: 'XLSX' },
  'application/vnd.ms-excel': { icon: File, label: 'XLS' },
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': { icon: File, label: 'PPTX' },
  'application/vnd.ms-powerpoint': { icon: File, label: 'PPT' },
};

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const UploadModal = () => {
  const { uploadModalOpen, toggleUploadModal } = useChatStore();
  const [dragOver, setDragOver] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('idle'); // idle, uploading, success, error
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    handleFiles(files);
  };

  const validateFile = (file) => {
    if (file.size > MAX_FILE_SIZE) {
      return `File "${file.name}" is too large. Maximum size is 10MB.`;
    }
    
    if (!SUPPORTED_TYPES[file.type]) {
      return `File type "${file.type}" is not supported.`;
    }
    
    return null;
  };

  const handleFiles = async (files) => {
    setError('');
    setUploadedFiles([]);
    
    // Validate all files first
    for (const file of files) {
      const validation = validateFile(file);
      if (validation) {
        setError(validation);
        return;
      }
    }

    setUploadStatus('uploading');
    const results = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      
      try {
        const response = await chatAPI.uploadFile(file, (progress) => {
          setUploadProgress(Math.round(((i * 100) + progress) / files.length));
        });
        
        results.push({
          name: file.name,
          status: 'success',
          message: response.message || 'File uploaded successfully'
        });
        
      } catch (error) {
        results.push({
          name: file.name,
          status: 'error',
          message: error.message || 'Upload failed'
        });
      }
    }

    setUploadedFiles(results);
    setUploadProgress(100);
    setUploadStatus('success');
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    if (uploadStatus !== 'uploading') {
      setUploadStatus('idle');
      setUploadProgress(0);
      setUploadedFiles([]);
      setError('');
      toggleUploadModal();
    }
  };

  const getFileIcon = (fileName) => {
    const extension = fileName.toLowerCase().split('.').pop();
    const mimeType = Object.keys(SUPPORTED_TYPES).find(type => 
      type.includes(extension) || SUPPORTED_TYPES[type].label.toLowerCase() === extension
    );
    
    if (mimeType && SUPPORTED_TYPES[mimeType]) {
      return SUPPORTED_TYPES[mimeType].icon;
    }
    
    return FileText;
  };

  return (
    <AnimatePresence>
      {uploadModalOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-gray-900/50 flex items-center justify-center z-50 p-4"
          onClick={handleClose}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-comviva-primary to-comviva-secondary rounded-full flex items-center justify-center shadow-sm">
                  <Upload className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-black">Upload Documents</h2>
                  <p className="text-sm text-gray-500 dark:text-dark-muted">Add files to your Comviva AI knowledge base</p>
                </div>
              </div>
              <button
                onClick={handleClose}
                disabled={uploadStatus === 'uploading'}
                className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6">
              {/* Upload Area */}
              {uploadStatus === 'idle' && (
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  className={`
                    border-2 border-dashed rounded-lg p-8 text-center transition-colors
                    ${dragOver 
                      ? 'border-comviva-primary bg-comviva-primary/5' 
                      : 'border-gray-300 hover:border-gray-400'
                    }
                  `}
                >
                  <Upload className={`
                    w-12 h-12 mx-auto mb-4
                    ${dragOver ? 'text-comviva-primary' : 'text-gray-400'}
                  `} />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    Drop files here or click to upload
                  </h3>
                  <p className="text-sm text-gray-500 mb-4">
                    Support for PDF, DOCX, DOC, TXT, MD, XLSX, XLS, PPTX, PPT
                  </p>
                  <p className="text-xs text-gray-400 mb-4">
                    Maximum file size: 10MB
                  </p>
                  
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.xls,.pptx,.ppt"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="btn-primary"
                  >
                    Choose Files
                  </button>
                </div>
              )}

              {/* Upload Progress */}
              {uploadStatus === 'uploading' && (
                <div className="text-center">
                  <Loader2 className="w-12 h-12 text-comviva-primary mx-auto mb-4 animate-spin" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    Processing your files...
                  </h3>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                    <div 
                      className="bg-comviva-primary h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <p className="text-sm text-gray-500">
                    {uploadProgress}% complete
                  </p>
                </div>
              )}

              {/* Results */}
              {(uploadStatus === 'success' || uploadedFiles.length > 0) && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Upload Results
                  </h3>
                  <div className="space-y-3 max-h-60 overflow-y-auto">
                    {uploadedFiles.map((file, index) => {
                      const FileIcon = getFileIcon(file.name);
                      return (
                        <div key={index} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                          <FileIcon className="w-5 h-5 text-gray-500 mt-0.5 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {file.name}
                            </p>
                            <p className={`text-xs mt-1 ${
                              file.status === 'success' ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {file.message}
                            </p>
                          </div>
                          {file.status === 'success' ? (
                            <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                          )}
                        </div>
                      );
                    })}
                  </div>
                  
                  <div className="mt-6 flex space-x-3">
                    <button
                      onClick={() => {
                        setUploadStatus('idle');
                        setUploadedFiles([]);
                        setUploadProgress(0);
                      }}
                      className="btn-secondary flex-1"
                    >
                      Upload More
                    </button>
                    <button
                      onClick={handleClose}
                      className="btn-primary flex-1"
                    >
                      Done
                    </button>
                  </div>
                </div>
              )}

              {/* Error Message */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                  <div className="flex items-start space-x-3">
                    <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <h3 className="text-sm font-medium text-red-800">Upload Error</h3>
                      <p className="text-sm text-red-700 mt-1">{error}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Supported Formats */}
              {uploadStatus === 'idle' && (
                <div className="mt-6">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">
                    Supported Formats:
                  </h4>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.values(SUPPORTED_TYPES).map((type, index) => (
                      <div key={index} className="flex items-center space-x-2 text-xs text-gray-500">
                        <type.icon className="w-3 h-3" />
                        <span>{type.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default UploadModal;