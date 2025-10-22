import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Trash2, Edit3, Check, X } from 'lucide-react';
import { format } from 'date-fns';

const ConversationItem = ({ 
  conversation, 
  isActive, 
  onClick, 
  onDelete, 
  onRename 
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(conversation.title || 'Untitled Chat');

  const handleEdit = (e) => {
    e.stopPropagation();
    setIsEditing(true);
  };

  const handleSave = (e) => {
    e.stopPropagation();
    if (editTitle.trim() && editTitle !== conversation.title) {
      onRename(conversation.session_id, editTitle.trim());
    }
    setIsEditing(false);
  };

  const handleCancel = (e) => {
    e.stopPropagation();
    setEditTitle(conversation.title || 'Untitled Chat');
    setIsEditing(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSave(e);
    } else if (e.key === 'Escape') {
      handleCancel(e);
    }
  };

  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM d, h:mm a');
    } catch {
      return 'Unknown';
    }
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`
        p-3 rounded-lg cursor-pointer transition-all duration-200 group relative
        ${isActive
          ? 'bg-comviva-primary/10 border border-comviva-primary/20 shadow-sm'
          : 'hover:bg-gray-50 dark:hover:bg-gray-700 border border-transparent'
        }
      `}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <div className="flex items-center space-x-2" onClick={(e) => e.stopPropagation()}>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onKeyDown={handleKeyDown}
                className="flex-1 text-sm font-medium bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-comviva-primary/50"
                autoFocus
              />
              <button
                onClick={handleSave}
                className="p-1 text-green-600 hover:text-green-700"
              >
                <Check className="w-3 h-3" />
              </button>
              <button
                onClick={handleCancel}
                className="p-1 text-gray-400 hover:text-gray-600"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <h4 className={`
              text-sm font-medium truncate
              ${isActive
                ? 'text-comviva-primary'
                : 'text-gray-900 dark:text-gray-100'
              }
            `}>
              {conversation.title || 'Untitled Chat'}
            </h4>
          )}
          
          <div className="flex items-center space-x-2 mt-1">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {conversation.message_count || 0} messages
            </span>
            <span className="text-gray-300 dark:text-gray-600">•</span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {formatDate(conversation.updated_at || conversation.created_at)}
            </span>
          </div>
        </div>
        
        {!isEditing && (
          <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleEdit}
              className="p-1 text-gray-400 hover:text-blue-500 transition-colors"
            >
              <Edit3 className="w-3 h-3" />
            </button>
            <button
              onClick={(e) => onDelete(e, conversation.session_id)}
              className="p-1 text-gray-400 hover:text-red-500 transition-colors"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>
      
      {/* Conversation preview */}
      {conversation.last_message && !isEditing && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 line-clamp-2">
          {conversation.last_message}
        </p>
      )}
    </motion.div>
  );
};

export default ConversationItem;