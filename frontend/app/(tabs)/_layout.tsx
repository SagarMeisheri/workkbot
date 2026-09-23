import { Tabs } from 'expo-router';
import { Text, View, StyleSheet } from 'react-native';

function TabIcon({ label, focused }: { label: string; focused: boolean }) {
  return (
    <View style={styles.iconContainer}>
      <Text style={[styles.iconText, focused && styles.iconTextFocused]}>
        {label === 'Chat' ? '💬' : label === 'Consent' ? '🛡️' : '⚙️'}
      </Text>
    </View>
  );
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: {
          backgroundColor: '#0F172A',
        },
        headerTintColor: '#F8FAFC',
        tabBarStyle: {
          backgroundColor: '#0F172A',
          borderTopColor: '#1E293B',
          height: 60,
          paddingBottom: 8,
          paddingTop: 8,
        },
        tabBarActiveTintColor: '#38BDF8',
        tabBarInactiveTintColor: '#64748B',
      }}
    >
      <Tabs.Screen
        name="chat"
        options={{
          title: 'Chat',
          headerTitle: 'Workkbot Sovereign AI',
          tabBarIcon: ({ focused }) => <TabIcon label="Chat" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="consent"
        options={{
          title: 'Consent',
          headerTitle: 'DPDP Consent Ledger',
          tabBarIcon: ({ focused }) => <TabIcon label="Consent" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Settings',
          headerTitle: 'Sovereignty & Privacy',
          tabBarIcon: ({ focused }) => <TabIcon label="Settings" focused={focused} />,
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  iconContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconText: {
    fontSize: 18,
    opacity: 0.6,
  },
  iconTextFocused: {
    opacity: 1,
  },
});
