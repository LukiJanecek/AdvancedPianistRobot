// app/(tabs)/_layout.tsx
import { Tabs } from "expo-router";
import { createContext, useContext, useRef } from "react";
import { Platform } from "react-native";

import { HapticTab } from "@/components/haptic-tab";
import { IconSymbol } from "@/components/ui/icon-symbol";
import { Colors } from "@/constants/theme";
import { useColorScheme } from "@/hooks/use-color-scheme";
import { useIsFocused } from "@react-navigation/native";

import { useWebSocket } from "@/hooks/useWebSocket";

const WebSocketContext = createContext<ReturnType<typeof useWebSocket> | null>(null);
export const useWs = () => {
  const ctx = useContext(WebSocketContext);
  if (!ctx) throw new Error("useWs must be used inside provider");
  return ctx;
};

export const unstable_settings = { initialRouteName: "songs" };

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const isFocused = useIsFocused();

  // stabilní device id pro celou appku
  const deviceRef = useRef<string | null>(null);
  if (!deviceRef.current) {
    const platform = Platform.OS ?? "unknown";
    const rand = Math.random().toString(36).slice(2, 8);
    const ts = Date.now().toString(36);
    deviceRef.current = `${platform}-${rand}-${ts}`;
  }

  // jediná WS instance
  const ws = useWebSocket({ device: deviceRef.current, desiredRole: "performer", echoSelf: false, enabled: isFocused });

  return (
    <WebSocketContext.Provider value={ws}>
      <Tabs
        screenOptions={{
          tabBarActiveTintColor: Colors[colorScheme ?? "light"].tint,
          headerShown: false,
          tabBarButton: HapticTab,
        }}
      >
        <Tabs.Screen
          name="piano"
          options={{
            title: "Piano",
            tabBarIcon: ({ color }) => (
              <IconSymbol size={28} name="pianokeys" color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="songs"
          options={{
            title: "Skladby",
            tabBarIcon: ({ color }) => (
              <IconSymbol size={28} name="music.note.list" color={color} />
            ),
          }}
        />
      </Tabs>
      
    </WebSocketContext.Provider>
  );
}
