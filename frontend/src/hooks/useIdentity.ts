import { useState } from "react";

const STORAGE_KEY_USER_ID = "finova_user_id";
const STORAGE_KEY_DISPLAY_NAME = "finova_display_name";

function generateUserId(): string {
  const rand = Math.random().toString(16).substring(2, 10);
  return `usr_${rand}`;
}

export function useIdentity() {
  const [userId, setUserId] = useState<string>(() => {
    const stored = localStorage.getItem(STORAGE_KEY_USER_ID);
    if (stored && stored.trim()) return stored.trim();
    const newId = generateUserId();
    localStorage.setItem(STORAGE_KEY_USER_ID, newId);
    return newId;
  });

  const [displayName, setDisplayNameState] = useState<string>(() => {
    return localStorage.getItem(STORAGE_KEY_DISPLAY_NAME) || "Learner";
  });

  const [isFirstLaunch, setIsFirstLaunch] = useState<boolean>(() => {
    return !localStorage.getItem(STORAGE_KEY_DISPLAY_NAME);
  });

  const setDisplayName = (name: string) => {
    const trimmed = name.trim() || "Learner";
    setDisplayNameState(trimmed);
    localStorage.setItem(STORAGE_KEY_DISPLAY_NAME, trimmed);
    setIsFirstLaunch(false);
  };

  const resetIdentity = () => {
    const newId = generateUserId();
    localStorage.setItem(STORAGE_KEY_USER_ID, newId);
    setUserId(newId);
  };

  return {
    userId,
    displayName,
    setDisplayName,
    resetIdentity,
    isFirstLaunch,
    setIsFirstLaunch,
  };
}
