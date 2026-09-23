import React from 'react';
import { SafeAreaView, StyleSheet } from 'react-native';
import { AssistantRuntimeProvider } from '@assistant-ui/react-native';
import { useAppRuntime } from '@/hooks/use-app-runtime';
import { Thread } from '@/components/Thread';

/**
 * Workkbot Sovereign Chat Screen
 * Fully powered by @assistant-ui/react-native runtime and primitives.
 */
export default function ChatScreen() {
  const runtime = useAppRuntime();

  return (
    <SafeAreaView style={styles.container}>
      <AssistantRuntimeProvider runtime={runtime}>
        <Thread />
      </AssistantRuntimeProvider>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#090D16',
  },
});
