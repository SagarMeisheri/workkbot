import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Platform,
  KeyboardAvoidingView,
} from 'react-native';
import {
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  AuiIf,
} from '@assistant-ui/react-native';

function UserMessage() {
  return (
    <MessagePrimitive.Root style={[styles.messageBubble, styles.userBubble]}>
      <MessagePrimitive.Content
        components={{
          Text: ({ children }) => <Text style={styles.userText}>{children}</Text>,
        }}
      />
    </MessagePrimitive.Root>
  );
}

function AssistantMessage() {
  return (
    <MessagePrimitive.Root style={[styles.messageBubble, styles.assistantBubble]}>
      <MessagePrimitive.Content
        components={{
          Text: ({ children }) => <Text style={styles.assistantText}>{children}</Text>,
        }}
      />
    </MessagePrimitive.Root>
  );
}

export function Thread() {
  return (
    <ThreadPrimitive.Root style={styles.container}>
      {/* Sovereign Session Status Badge */}
      <View style={styles.sovereignBadge}>
        <Text style={styles.badgeText}>
          🛡️ Sovereign Session: asia-south1 (Mumbai) | ZDR Active
        </Text>
      </View>

      {/* Empty State */}
      <AuiIf condition={(s) => s.thread.isEmpty}>
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>🇮🇳</Text>
          <Text style={styles.emptyTitle}>Sovereign Enterprise Assistant</Text>
          <Text style={styles.emptySubtitle}>
            Your messages and data are pinned strictly to Mumbai. Ask a question or manage your tasks.
          </Text>
        </View>
      </AuiIf>

      {/* Message Viewport */}
      <ThreadPrimitive.MessagesFlatList
        style={styles.messageList}
        contentContainerStyle={styles.messageListContent}
        autoScroll
        components={{
          UserMessage,
          AssistantMessage,
        }}
      />

      {/* Typing Indicator */}
      <AuiIf condition={(s) => s.thread.isRunning}>
        <View style={styles.runningIndicator}>
          <ActivityIndicator size="small" color="#38BDF8" />
          <Text style={styles.runningText}>Generating response in asia-south1...</Text>
        </View>
      </AuiIf>

      {/* Composer Input Area */}
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        <ComposerPrimitive.Root style={styles.inputContainer}>
          <ComposerPrimitive.Input
            style={styles.textInput}
            placeholder="Ask Workkbot..."
            placeholderTextColor="#94A3B8"
            multiline
          />
          <ComposerPrimitive.Send style={styles.sendButton}>
            <Text style={styles.sendButtonText}>Send</Text>
          </ComposerPrimitive.Send>
        </ComposerPrimitive.Root>
      </KeyboardAvoidingView>
    </ThreadPrimitive.Root>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#090D16',
  },
  sovereignBadge: {
    backgroundColor: '#0F2942',
    paddingVertical: 6,
    paddingHorizontal: 12,
    marginHorizontal: 16,
    marginTop: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#0284C7',
    alignItems: 'center',
  },
  badgeText: {
    color: '#38BDF8',
    fontSize: 12,
    fontWeight: '600',
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#F8FAFC',
    marginBottom: 8,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#94A3B8',
    textAlign: 'center',
    lineHeight: 20,
  },
  messageList: {
    flex: 1,
  },
  messageListContent: {
    padding: 16,
    gap: 12,
  },
  messageBubble: {
    maxWidth: '82%',
    padding: 12,
    borderRadius: 12,
    marginBottom: 8,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: '#0284C7',
    borderBottomRightRadius: 2,
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    backgroundColor: '#1E293B',
    borderBottomLeftRadius: 2,
  },
  userText: {
    color: '#FFFFFF',
    fontSize: 15,
    lineHeight: 21,
  },
  assistantText: {
    color: '#F1F5F9',
    fontSize: 15,
    lineHeight: 21,
  },
  runningIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 6,
    gap: 8,
  },
  runningText: {
    color: '#94A3B8',
    fontSize: 12,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#0F172A',
    borderTopWidth: 1,
    borderTopColor: '#1E293B',
    alignItems: 'center',
    gap: 8,
  },
  textInput: {
    flex: 1,
    backgroundColor: '#1E293B',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    color: '#FFFFFF',
    fontSize: 15,
    maxHeight: 120,
  },
  sendButton: {
    backgroundColor: '#0284C7',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonText: {
    color: '#FFFFFF',
    fontWeight: '600',
    fontSize: 14,
  },
});
