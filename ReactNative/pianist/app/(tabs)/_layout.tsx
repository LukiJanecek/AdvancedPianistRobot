import { Tabs } from 'expo-router';
import React from 'react';

import { HapticTab } from '@/components/haptic-tab';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';

export const unstable_settings = { initialRouteName: '(tabs)' };

export default function TabLayout() {
  const colorScheme = useColorScheme();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? 'light'].tint,
        headerShown: false,
        tabBarButton: HapticTab,
      }}>
      <Tabs.Screen
        name="piano_be"
        options={{
          title: 'Pianist BE',
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="pianokeys" color={color} />,
        }}
      />
      <Tabs.Screen
        name="piano_fe"
        options={{
          title: 'Pianist FE',
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="pianokeys" color={color} />,
        }}
      />
      <Tabs.Screen
        name="songs_be"
        options={{
          title: 'Songs BE',
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="pianokeys" color={color} />,
        }}
      />
      <Tabs.Screen
        name="songs_fe"
        options={{
          title: 'Songs FE',
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="pianokeys" color={color} />,
        }}
      />
    </Tabs>
  );
}
