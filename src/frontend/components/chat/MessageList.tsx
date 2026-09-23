"use client";

import React, { useEffect, useRef } from "react";
import { ChatMessage } from "@/types/api";
import { ChatMessageItem } from "@/components/chat/ChatMessageItem";

export interface MessageListProps {
  messages: ChatMessage[];
  isLoading?: boolean;
  isApprovingHitl?: boolean;
  onApproveHitl?: (approved: boolean, reason?: string) => void;
  onSelectOption?: (option: string) => void;
  onRetry?: () => void;
  className?: string;
}

export function MessageList({
  messages,
  isLoading = false,
  isApprovingHitl = false,
  onApproveHitl,
  onSelectOption,
  onRetry,
  className = "",
}: MessageListProps) {
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Tự động cuộn xuống cuối khi có tin nhắn mới hoặc trạng thái loading thay đổi
  useEffect(() => {
    if (messages.length > 0) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading]);

  return (
    <div
      className={`space-y-2 pb-6 ${className}`}
      role="feed"
      aria-label="Dòng hội thoại phân tích dữ liệu"
    >
      {messages.map((msg) => (
        <ChatMessageItem
          key={msg.id}
          message={msg}
          isGlobalLoading={isLoading}
          isApprovingHitl={isApprovingHitl}
          onApproveHitl={onApproveHitl}
          onSelectOption={onSelectOption}
          onRetry={onRetry}
        />
      ))}
      <div ref={chatEndRef} data-testid="chat-end-anchor" />
    </div>
  );
}

export default MessageList;
