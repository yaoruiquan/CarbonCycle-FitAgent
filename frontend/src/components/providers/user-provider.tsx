"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { userStorage } from "@/lib/storage";
import { userApi } from "@/lib/api";

interface UserContextType {
    userId: string | null;
    user: any | null;
    loading: boolean;
    login: (id: string) => Promise<void>;
    logout: () => void;
    refresh: () => Promise<void>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: React.ReactNode }) {
    const [userId, setUserId] = useState<string | null>(null);
    const [user, setUser] = useState<any | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchUser = async (id: string) => {
        try {
            const data = await userApi.get(id);
            setUser(data);
        } catch (err) {
            console.error("Failed to fetch user", err);
            // If error (e.g. user deleted), clear local storage
            userStorage.clearUserId();
            setUserId(null);
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const id = userStorage.getUserId();
        if (id) {
            setUserId(id);
            fetchUser(id);
        } else {
            setLoading(false);
        }
    }, []);

    const login = async (id: string) => {
        setLoading(true);
        userStorage.setUserId(id);
        setUserId(id);
        await fetchUser(id);
    };

    const logout = () => {
        userStorage.clearUserId();
        setUserId(null);
        setUser(null);
    };

    const refresh = async () => {
        if (userId) {
            await fetchUser(userId);
        }
    };

    return (
        <UserContext.Provider value={{ userId, user, loading, login, logout, refresh }}>
            {children}
        </UserContext.Provider>
    );
}

export function useUser() {
    const context = useContext(UserContext);
    if (context === undefined) {
        throw new Error("useUser must be used within a UserProvider");
    }
    return context;
}
