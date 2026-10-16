import React, { useState } from "react";
import { useIdentity } from "./hooks/useIdentity";
import { useChat } from "./hooks/useChat";
import { useTheme } from "./hooks/useTheme";
import { Header } from "./components/layout/Header";
import { Sidebar } from "./components/layout/Sidebar";
import { MessageList } from "./components/chat/MessageList";
import { ChatInput } from "./components/chat/ChatInput";
import { ProfileModal } from "./components/memory/ProfileModal";
import type { TutorSectionId } from "./api/types";

export const App: React.FC = () => {
  useTheme(); // Initializes and synchronizes active theme
  const { userId, displayName, setDisplayName } = useIdentity();
  const [activeSection, setActiveSection] = useState<TutorSectionId>("general");

  const {
    activeConversationId,
    messages,
    isLoading,
    activeElapsed,
    error,
    sendMessage,
    loadConversation,
    newConversation,
  } = useChat(userId, activeSection);

  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [historyRefresh, setHistoryRefresh] = useState(0);

  const handleSelectSection = (sectionId: TutorSectionId) => {
    setActiveSection(sectionId);
    newConversation(sectionId);
  };

  const handleSelectConversation = async (conversationId: string) => {
    const loadedDomain = await loadConversation(conversationId);
    if (loadedDomain) {
      // Invariant 4: Reopening a conversation must automatically switch the UI to that conversation's stored tutor/domain
      setActiveSection(loadedDomain as TutorSectionId);
    }
  };

  const handleNewChat = (domain?: TutorSectionId) => {
    const target = domain || activeSection;
    setActiveSection(target);
    newConversation(target);
  };

  const handleSelectPrompt = (prompt: string) => {
    sendMessage(prompt, activeSection);
  };

  const handleRetry = (query: string) => {
    sendMessage(query, activeSection);
  };

  const handleClearAllConversations = () => {
    newConversation(activeSection);
    setHistoryRefresh((prev) => prev + 1);
  };

  return (
    <div className="flex h-screen bg-espresso text-ivory font-sans antialiased overflow-hidden">
      {/* Collapsible Left Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onSelectPrompt={handleSelectPrompt}
        onOpenProfile={() => setIsProfileOpen(true)}
        userId={userId}
        displayName={displayName}
        activeConversationId={activeConversationId}
        activeSection={activeSection}
        onSelectSection={handleSelectSection}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        refreshTrigger={historyRefresh}
      />

      {/* Main Assistant Body */}
      <div className="flex-1 flex flex-col min-w-0 h-full">
        <Header
          displayName={displayName}
          userId={userId}
          activeSection={activeSection}
          onOpenProfile={() => setIsProfileOpen(true)}
          onNewChat={() => handleNewChat(activeSection)}
          onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
        />

        <main className="flex-1 flex flex-col min-h-0 relative">
          <MessageList
            messages={messages}
            isLoading={isLoading}
            elapsedSeconds={activeElapsed}
            error={error}
            activeSection={activeSection}
            displayName={displayName}
            userId={userId}
            onSelectPrompt={handleSelectPrompt}
            onContinueLearning={handleSelectConversation}
            onRetry={handleRetry}
          />

          <ChatInput
            onSendMessage={(query) => sendMessage(query, activeSection)}
            isLoading={isLoading}
          />
        </main>
      </div>

      {/* Identity, Memory & Settings Modal */}
      <ProfileModal
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
        userId={userId}
        displayName={displayName}
        setDisplayName={setDisplayName}
        onClearAllConversations={handleClearAllConversations}
      />
    </div>
  );
};

export default App;
