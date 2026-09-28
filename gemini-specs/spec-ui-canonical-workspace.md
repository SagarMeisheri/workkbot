# Spec UI: Canonical Assistant-UI Workspace, Floating Composer & Action Popover

## 1. Context & Motivation
The visual and interactive surface of Workkbot directly defines employee adoption, trust, and perceived quality. The user experience must deliver a state-of-the-art, clutter-free conversational environment matching top-tier generative AI interfaces (such as Claude 3.7 / ChatGPT Canvas and the canonical **assistant-ui** design system), while strictly routing every state, model call, and tool execution through the **5 Core Frameworks** (**Supabase**, **GCP**, **Google ADK 2.0**, **assistant-ui**, and **Agentgateway**).

This specification details the pixel-level layout, component hierarchy, interactive state machines, and styling tokens for the **two target UI states**:
1. **State 1: Cold Landing / Unauthenticated Thread ("How can I help you today?")**:
   - Collapsible left sidebar with app branding, `[\|]` toggle, prominent `+ New thread` pill, empty session state, and bottom `-> Sign in` action.
   - Clean top header with thread title (`New chat`), options (`...`), and canvas split toggle (`↗`).
   - Centered hero heading: **"How can I help you today?"**.
   - Floating composer container embedding `+` trigger, `ModelSelector` (`GPT-6 Luna` / `Gemini 2.0 Flash`), speech-to-text microphone, and send button (`↑`).
   - Centered staggered prompt suggestion cloud.
2. **State 2: Authenticated Returning Workspace ("✳ Back at it, [name]") with Active `+` Popover**:
   - Personalized hero greeting featuring the warm brand sunburst glyph (`✳`) and serif typography (`Back at it, sagar`).
   - Floating composer with active dual-mode pill toggle: `[ Chat | Cowork ]` (or `[ Chat | Canvas ]`).
   - Active hierarchical **Plus (`+`) Action Popover Menu** featuring:
     - `📎 Add files or photos` (`⌘U`)
     - `📷 Take a screenshot`
     - `📁 Add to project >`
     - `📑 Skills >` (Spec 08)
     - `🔲 Connectors >` (Spec 01/05 Connectors Hub Modal)
     - `🎨 Design system >`
     - `🧩 Add plugins` (Spec 05 OpenAPI virtualizer)
     - Divider line
     - `🌐 Web search` (`✓` toggle for Google Search Grounding)
   - Model selection (`Sonnet 5 Medium` / `Gemini 2.0 Flash Medium`), dictation mic, and real-time voice waveform/orb (`|||| ▾`).

### **The North Star: Security & Mobile App Approval**
- **Security**: The UI never exposes raw OAuth tokens or unmasked Indian PII. Auth gates seamlessly at the composer boundary; user data deletion is directly accessible via the profile footer.
- **Mobile App Approval (Apple App Store & Google Play)**: The entire layout transitions responsively to `@assistant-ui/react-native` (Expo SDK 52). Every message bubble includes an instant **"Report / Flag AI Response"** button in `ActionBarPrimitive` (Apple Guideline 1.2), a one-tap in-app account deletion entry point in the profile settings (Apple Guideline 5.1.1), and an unauthenticated Reviewer Sandbox toggle (Apple Guideline 2.1).

---

## 2. The 5-Framework Architecture Mapping for Spec UI

| Framework | Core Responsibility in UI Execution | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | Provides auth state driving sidebar footer (`-> Sign in` vs avatar), employee name for greeting (`Back at it, [name]`), Realtime notification badges, and Vault token status. | RLS ensures only the active user's threads appear in the sidebar; one-click in-app account deletion completely purges user data (Apple 5.1.1). |
| **2. Google Cloud Platform (GCP)** | Cloud Run hosts the Next.js 15 SSR frontend; Cloud Armor protects endpoints; Vertex AI powers Google Search Grounding (`Web search ✓`); GCS backs artifact canvas. | Direct VPC Egress blocks container SSRF; Google Search grounding runs via verified Vertex AI Search API without leaking user IP. |
| **3. Google ADK 2.0** | In-process Python Runner handling multi-turn sessions; `before_model` skills injection for `Skills >`; pauses execution for inline `ApprovalCard`. | Checkpoint-based event trees map cleanly to assistant-ui's branch picker; prevents unauthenticated tool dispatch. |
| **4. assistant-ui** | Powers all visual primitives: `ThreadListSidebar`, `ComposerPrimitive`, `AttachmentPrimitive`, `ModelSelector`, `SuggestionPrimitive`, `Reasoning`, `Sources`, and `ActionBarPrimitive`. | Provides guaranteed 60fps mobile parity via `@assistant-ui/react-native`; embeds mandatory Apple 1.2 AI report flag modal. |
| **5. Agentgateway 1.5.x** | Proxies tool connections initiated via `Connectors >` and `Add plugins`; routes model requests to Vertex AI with circuit-breaker failover; blocks prompt injection in tool definitions. | CEL policies restrict tool execution to authorized roles; strips indirect injection from third-party tool metadata. |

---

## 3. Detailed Component Hierarchy & Layout Anatomy

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                      TOP HEADER BAR                                                    │
│ [\|] (Sidebar Toggle)  |  "New chat" (Thread Title)                        [...] (Options)  |  [↗] (Canvas Toggle)    │
├────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────┤
│    COLLAPSIBLE         │                                      MAIN STAGE                                               │
│    LEFT SIDEBAR        │                                                                                               │
│                        │                                                                                               │
│ [ICON] assistant-ui [\|]│                                    HERO GREETING                                             │
│                        │              State 1: "How can I help you today?" (Bold Sans, 32px)                           │
│ ┌────────────────────┐ │              State 2: "✳ Back at it, sagar" (Serif Typography, 32px)                           │
│ │ + New thread       │ │                                                                                               │
│ └────────────────────┘ │                                                                                               │
│                        │                          FLOATING COMPOSER CONTAINER                                          │
│  Conversation Threads  │       ┌───────────────────────────────────────────────────────────────────────────────┐       │
│  • Today               │       │ Send a message... / How can I help you today?                                 │       │
│  • Previous 7 Days     │       │                                                                               │       │
│  • Older               │       │ ┌───┐ ┌──────────────┐                       ┌───────────────┐ ┌───┐ ┌─────┐ ┌─────┐ │       │
│                        │       │ │ + │ │[Chat|Cowork] │                       │ ModelSelector │ │🎙️ │ │||||▾│ │  ↑  │ │       │
│                        │       │ └───┘ └──────────────┘                       └───────────────┘ └───┘ └─────┘ └─────┘ │       │
│                        │       └─┬─────────────────────────────────────────────────────────────────────────────┘       │
│                        │         │                                                                                     │
│                        │         ▼ (OPENED POPOVER)                                                                    │
│                        │       ┌──────────────────────────────────────────────┐                                        │
│                        │       │ 📎 Add files or photos                    ⌘U │                                        │
│                        │       │ 📷 Take a screenshot                         │                                        │
│                        │       │ 📁 Add to project                          > │                                        │
│                        │       │ 📑 Skills                                  > │                                        │
│                        │       │ 🔲 Connectors                              > │                                        │
│                        │       │ 🎨 Design system                           > │                                        │
│                        │       │ 🧩 Add plugins                               │                                        │
│                        │       │ ──────────────────────────────────────────── │                                        │
│                        │       │ 🌐 Web search                              ✓ │                                        │
│                        │       └──────────────────────────────────────────────┘                                        │
│                        │                                                                                               │
│                        │                             SUGGESTION CLOUD                                                  │
│                        │     ┌──────────────────┐  ┌───────────────────────┐  ┌─────────────────────┐                  │
│                        │     │ Weather in Tokyo │  │ Show a sales dashboard│  │ Switch to dark mode │                  │
│                        │     └──────────────────┘  └───────────────────────┘  └─────────────────────┘                  │
│                        │     ┌────────────────────────────┐  ┌─────────────────────────────┐  ┌──────────────────┐     │
│                        │     │ Derive the geometric series│  │ Diagram a streaming chat app│  │ Add a thread list│     │
│                        │     └────────────────────────────┘  └─────────────────────────────┘  └──────────────────┘     │
│                        │                                ┌──────────────────┐                                           │
│                        │                                │ Remember my stack│                                           │
│                        │                                └──────────────────┘                                           │
│                        │                                                                                               │
│ ────────────────────── │                                                                                               │
│ [->] Sign in           │                                                                                               │
│ (or User Avatar/Org)   │                                                                                               │
└────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component-by-Component Technical Specifications

### 4.1. Collapsible Left Sidebar (`ThreadListSidebar`)
- **Package**: `@assistant-ui/react` elements catalog (`components/assistant-ui/elements/thread-list-sidebar.aui.tsx`).
- **Layout Tokens**:
  - Width: `w-64` (256px) expanded, `w-0` collapsed with smooth CSS transition (`transition-all duration-300 ease-in-out`).
  - Background: `bg-sidebar` (`#fafafa` in light mode, `#121212` in dark mode).
  - Border: `border-r border-sidebar-border` (`#e5e5e5` / `#262626`).
- **Header Elements**:
  - Brand Logo & Title: assistant-ui chat bubble glyph + `"assistant-ui"` (or `"Workkbot"` in production) in `font-medium text-sm`.
  - Collapse Toggle Icon: `[\|]` button (`SidebarPrimitive.Toggle`) collapsing the drawer.
- **Action Button: `+ New thread`**:
  - Component: `ThreadListPrimitive.New`.
  - Styling: Rounded pill (`rounded-full border border-border bg-white dark:bg-zinc-900 shadow-xs hover:bg-accent px-4 py-2 text-sm font-medium flex items-center gap-2`).
  - Action: Dispatches `aui.threads.switchToNew()`, resetting conversation context and presenting the centered landing state.
- **Thread History Area**:
  - Component: `ThreadListPrimitive.Items`.
  - Categorization: Grouped by date buckets: *Today*, *Yesterday*, *Previous 7 Days*, *Older*.
  - Item Actions: Hover reveals three dots `...` supporting **Rename**, **Archive**, and **Delete**.
- **Footer: Identity & Auth State (`SidebarAuthFooter`)**:
  - **Unauthenticated (State 1)**:
    - Button: `-> Sign in` icon and text.
    - Behavior: Clicking opens Google Workspace OAuth login popup or redirects to `/login`.
  - **Authenticated (State 2)**:
    - Profile avatar with initial/image.
    - Employee Name (`sagar`) + Organization badge (`Workkbot SMB`).
    - Clicking opens user settings: Preferences, DPDP Privacy Portal, and **[Delete Account & Purge Memory]** (Apple Guideline 5.1.1).

---

### 4.2. Top Navigation Header (`ThreadHeader`)
- **Component**: `components/chat/thread-header.tsx`.
- **Layout**:
  - Height: `h-14` (56px), flex items center, space between.
  - Border: Subtly bordered at bottom (`border-b border-border/40`).
- **Left Slot**:
  - Active thread title (default: `"New chat"` on cold landing; automatically updated to conversation topic after first turn).
- **Right Slot**:
  - Options Menu `...`: Thread export, share link, clear messages.
  - **Canvas Toggle Button `↗`**:
    - Toggles dual-pane split screen for Spec 07 Generative Artifacts.
    - When active, the main viewport splits 50/50 between the chat stream and the sandboxed iframe canvas (`AssistantFrameProvider`).

---

### 4.3. Hero Greeting Variations
The main stage dynamically displays one of two hero typography variants:

1. **State 1: Cold / Generic Hero Greeting**:
   ```tsx
   <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-foreground text-center my-6">
     How can I help you today?
   </h1>
   ```
   - Font: Inter / Outfit, `font-semibold`, crisp neutral color.

2. **State 2: Authenticated / Personalized Returning Hero**:
   ```tsx
   <div className="flex items-center justify-center gap-3 my-6">
     <span className="text-amber-600 dark:text-amber-500 text-3xl select-none">✳</span>
     <h1 className="text-3xl sm:text-4xl font-serif font-normal text-foreground">
       Back at it, {user?.user_metadata?.first_name || 'sagar'}
     </h1>
   </div>
   ```
   - Icon: Warm amber eight-point sunburst glyph (`✳`).
   - Font: Modern serif (e.g., Newsreader, Merriweather, or Georgia), creating an inviting, editorial feel.

---

### 4.4. Floating Composer Bar (`ComposerPrimitive.Root`)
The central interaction container is an elevated, floating capsule positioned centrally during the empty landing state and anchored at the bottom during active conversation.

- **Container Styling**:
  - Width: `w-full max-w-2xl` (672px).
  - Shape: Rounded rectangle (`rounded-2xl` with 16px radius).
  - Background: `bg-card` (`#ffffff` / `#18181b`).
  - Border & Shadow: `border border-border shadow-md dark:shadow-none`.
  - Padding: `p-3.5 flex flex-col gap-2.5`.

- **Top Area: Text Input (`ComposerPrimitive.Input`)**:
  - Multi-line autosizing textarea (`min-h-[48px] max-h-48 resize-none bg-transparent outline-none text-base text-foreground placeholder:text-muted-foreground/80`).
  - Placeholder: `"Send a message..."` (State 1) or `"How can I help you today?"` (State 2).
  - Slash Command Detection: Typing `/` immediately opens the inline Skill / Command popover (`/gst`, `/tally`, `/invoice`, `/help`).

- **Bottom Action Bar**:
  A horizontal flex row (`flex items-center justify-between pt-1`):

  - **Left Cluster**:
    1. **Plus (`+`) Action Button (`ComposerPrimitive.AddAttachment` / Popover Trigger)**:
       - Circle or rounded button (`h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent`).
       - Clicking opens the **Hierarchical Action Popover** (detailed in Section 4.5).
    2. **Segmented Mode Pill `[ Chat | Cowork ]`**:
       - Container: Rounded pill (`rounded-full bg-muted/60 p-0.5 flex items-center text-xs font-medium`).
       - Active Tab (`Chat`): `rounded-full bg-background shadow-xs text-foreground px-2.5 py-1`.
       - Inactive Tab (`Cowork` / `Canvas`): `text-muted-foreground hover:text-foreground px-2.5 py-1 transition-colors`.
       - Behavior: Toggling to `Cowork` / `Canvas` instructs the ADK agent to prefer producing full-page artifacts and opens the right-hand Canvas split pane (`↗`).

  - **Right Cluster**:
    1. **`ModelSelector` Pill**:
       - Pill layout: Model brand icon + model name + tier pill + dropdown caret `v`.
       - Options:
         - `Gemini 2.0 Flash` (`Low` latency / general tasks)
         - `Gemini 2.0 Pro` (`High` reasoning / complex coding)
       - Routing: Directly passes selected tier headers to Agentgateway (`http://127.0.0.1:8080/v1`).
    2. **Speech-to-Text Microphone (`ComposerPrimitive.Speech`)**:
       - Button with microphone icon (`🎙️`).
       - Behavior: Emits browser SpeechRecognition audio transcription into `ComposerPrimitive.Input`.
    3. **Voice Orb / Waveform Indicator**:
       - Visual: 4-bar dynamic audio equalizer icon (`|||| ▾`).
       - Behavior: Toggles bidirectional voice mode with Gemini Live API / audio streaming.
    4. **Send Button (`ComposerPrimitive.Send`)**:
       - Elevated circular button (`h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center disabled:opacity-40`).
       - Up-arrow icon (`↑`).
       - Shortcut: `Enter` to send, `Shift+Enter` for newline.

---

### 4.5. The Plus (`+`) Hierarchical Action Popover
Clicking `+` mounts a floating popover anchored directly below the button:

```tsx
<PopoverContent align="start" sideOffset={8} className="w-64 p-1.5 rounded-xl shadow-xl border bg-popover text-popover-foreground">
  <div className="flex flex-col gap-0.5 text-sm">
    {/* Item 1: Files */}
    <button className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-accent text-left">
      <div className="flex items-center gap-2.5">
        <Paperclip className="h-4 w-4 text-muted-foreground" />
        <span>Add files or photos</span>
      </div>
      <kbd className="text-xs text-muted-foreground font-mono">⌘U</kbd>
    </button>

    {/* Item 2: Screenshot */}
    <button className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-accent text-left">
      <Camera className="h-4 w-4 text-muted-foreground" />
      <span>Take a screenshot</span>
    </button>

    {/* Item 3: Project Binding */}
    <button className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-accent text-left">
      <div className="flex items-center gap-2.5">
        <Folder className="h-4 w-4 text-muted-foreground" />
        <span>Add to project</span>
      </div>
      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
    </button>

    {/* Item 4: Skills (Spec 08) */}
    <button className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-accent text-left">
      <div className="flex items-center gap-2.5">
        <FileText className="h-4 w-4 text-muted-foreground" />
        <span>Skills</span>
      </div>
      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
    </button>

    {/* Item 5: Connectors (Spec 01/05) */}
    <button 
      onClick={() => openConnectorsModal()} 
      className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-accent text-left"
    >
      <div className="flex items-center gap-2.5">
        <Grid className="h-4 w-4 text-muted-foreground" />
        <span>Connectors</span>
      </div>
      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
    </button>

    {/* Item 6: Design System */}
    <button className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-accent text-left">
      <div className="flex items-center gap-2.5">
        <Palette className="h-4 w-4 text-muted-foreground" />
        <span>Design system</span>
      </div>
      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
    </button>

    {/* Item 7: Plugins */}
    <button className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-accent text-left">
      <Puzzle className="h-4 w-4 text-muted-foreground" />
      <span>Add plugins</span>
    </button>

    {/* Divider */}
    <div className="my-1 border-t border-border" />

    {/* Item 8: Web Search Grounding Toggle */}
    <button 
      onClick={() => toggleWebSearch()} 
      className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-accent text-left"
    >
      <div className="flex items-center gap-2.5">
        <Globe className="h-4 w-4 text-muted-foreground" />
        <span>Web search</span>
      </div>
      {webSearchEnabled && <Check className="h-4 w-4 text-primary" />}
    </button>
  </div>
</PopoverContent>
```

---

### 4.6. Suggestion Prompt Cloud (`SuggestionPrimitive`)
Directly below the composer, staggered suggestion pills guide users to high-value workflows:

- **Row 1**:
  - `[ Weather in Tokyo ]`
  - `[ Show a sales dashboard ]`
  - `[ Switch to dark mode ]`
- **Row 2**:
  - `[ Derive the geometric series ]`
  - `[ Diagram a streaming chat app ]`
  - `[ Add a thread list ]`
- **Row 3**:
  - `[ Remember my stack ]`

- **Indian SMB Localization Overrides**:
  For Indian corporate deployments, suggestion chips dynamically adjust based on connected MCP tools:
  - `[ Compute March GST ]`
  - `[ Zoho unpaid invoices ]`
  - `[ Tally stock ledger ]`
  - `[ What does AI remember about me? ]`

- **Interaction**: Clicking any chip calls `aui.composer.setText(chip.prompt)` and auto-dispatches via `aui.composer.send()`.

---

## 5. Mobile Parity via `@assistant-ui/react-native` (Expo SDK 52)

To satisfy the **Mobile App Approval North Star**:
1. **Responsive Viewport Adaptation**:
   - On screens `<768px` (iOS & Android):
     - The left sidebar collapses into an Expo slide-over drawer triggered by a hamburger icon `☰`.
     - The hero greeting reduces to `text-2xl`.
     - The composer bar adapts into a bottom-docked keyboard-avoiding capsule (`KeyboardAvoidingView`).
     - The `+` menu opens as a native bottom sheet modal (`@gorhom/bottom-sheet`).
2. **Apple App Store Review Guidelines Compliance**:
   - **Guideline 1.2 (AI Safety)**: Every message in `@assistant-ui/react-native` embeds an `ActionBarPrimitive` with a prominent **Flag / Report** button opening the in-app reporting dialog.
   - **Guideline 2.1 (Reviewer Mode)**: Login screen exposes a test button for `apple-reviewer@workkbot.in` pre-seeded with demo data.
   - **Guideline 5.1.1 (Account Deletion)**: Settings screen has a dedicated **[Delete Account & Purge Memory]** button triggering atomic DSR erasure in Supabase.

---

## 6. Implementation File Deliverables

The UI components will be organized under the following modular paths:
1. `apps/web/src/components/chat/`
   - `adk-chat-container.tsx`: Root client provider mounting `useAdkRuntime`.
   - `chat-hero-greeting.tsx`: Switches between `"How can I help you today?"` and `"✳ Back at it, [name]"`.
   - `floating-composer.tsx`: Floating capsule embedding input, mode toggle, model selector, and mic.
   - `composer-plus-popover.tsx`: The 8-item hierarchical action popover.
   - `suggestion-cloud.tsx`: Staggered prompt chips.
   - `thread-header.tsx`: Header title, options `...`, and canvas toggle `↗`.
2. `apps/web/src/components/sidebar/`
   - `sidebar-auth-footer.tsx`: Canonical sidebar footer toggling between `-> Sign in` and user avatar/settings.
3. `apps/mobile/src/components/chat/`
   - `MobileComposer.tsx`: React Native equivalent of the floating composer.
   - `MobileActionSheet.tsx`: Native bottom sheet implementation of the `+` menu.
   - `MobileActionBar.tsx`: Message action bar with Apple 1.2 report flag.

---

## 7. Validation Scorecard & Execution Target

### **Execution Target**: `Localhost (Zero-Mock)`
- **Environment**: Next.js 15 (`localhost:3000`) and React Native Expo SDK 52 simulator.
- **Live Cloud Boundaries**: Live Supabase Mumbai (`ap-south-1`) for authentication state, profile first name lookup (`public.profiles`), and live incident reporting (`public.ai_content_reports`). No hardcoded mock names or synthetic thread arrays permitted.

---

### **Tier 1: Component Unit & Style Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-UI.1** | Component typecheck and Tailwind CSS token build passes without circular dependencies | `pnpm --filter @workkbot/web typecheck` | [ ] |
| **VAL-UI.2** | Plus popover menu items adhere to accessibility specifications and keyboard navigation | `pnpm --filter @workkbot/web test tests/unit/composer-plus-popover.test.tsx` | [ ] |

### **Tier 2: Zero-Mock Live Wire Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-UI.3** | Live Supabase session injects user first name into State 2 hero greeting (`Back at it, [name]`) | `pnpm --filter @workkbot/web test:e2e tests/e2e/live-hero-greeting.spec.ts` | [ ] |
| **VAL-UI.4** | Submitting Apple 1.2 Flag Modal writes live incident report to Supabase `ai_content_reports` | `pnpm --filter @workkbot/web test:e2e tests/e2e/live-ai-flagging.spec.ts` | [ ] |

### **Tier 3: UI & Front-End E2E Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-UI.5** | Empty unauthenticated thread renders centered hero *"How can I help you today?"* and suggestion chips | `pnpm --filter @workkbot/web test:e2e tests/e2e/landing-state.spec.ts` | [ ] |
| **VAL-UI.6** | Authenticated user sees *"✳ Back at it, [name]"* with serif font and warm sunburst icon | `pnpm --filter @workkbot/web test:e2e tests/e2e/returning-hero.spec.ts` | [ ] |
| **VAL-UI.7** | Clicking `+` opens hierarchical popover with all 8 items and keyboard shortcuts (`⌘U`) | `pnpm --filter @workkbot/web test:e2e tests/e2e/composer-popover.spec.ts` | [ ] |
| **VAL-UI.8** | Toggling `[Chat \| Cowork]` switches state and triggers Canvas split `↗` | `pnpm --filter @workkbot/web test:e2e tests/e2e/mode-toggle.spec.ts` | [ ] |
| **VAL-UI.9** | Model selector pill toggles between Vertex AI Gemini Flash and Pro tiers | `pnpm --filter @workkbot/web test:e2e tests/e2e/model-selector.spec.ts` | [ ] |
| **VAL-UI.10** | Mobile client renders responsive layout with native bottom sheet `+` menu | `pnpm --filter @workkbot/mobile test:e2e tests/e2e/mobile-composer.spec.ts` | [ ] |

### **Tier 4: Manual Verification Protocol**
1. **State 1 (Cold / Unauthenticated)**: Open incognito tab to `http://localhost:3000`. Confirm centered hero *"How can I help you today?"* renders in bold sans typography with staggered prompt chips below. Confirm sidebar footer displays `-> Sign in`.
2. **State 2 (Authenticated)**: Log in as reviewer or employee. Confirm hero greeting transitions smoothly to *"✳ Back at it, [firstName]"* with elegant serif typography and brand glyph. Confirm sidebar footer displays user avatar and email.
3. **Floating Composer & Plus Popover**:
   - Press `+` button in composer: confirm dropdown displays 8 items with clean category dividers.
   - Press `⌘U`: confirm native file picker opens (`Add files or photos`).
   - Click `Connectors >`: confirm Connectors Hub Modal opens centered over the workspace.
4. **Dual Mode Toggle**: Click `Cowork` (or `Canvas ↗`). Verify screen splits into 50/50 dual pane (Left: Chat stream, Right: Artifact Canvas).
5. **Apple 1.2 Report Flag**: Hover over any AI message bubble, click Flag icon. Confirm dialog opens with reason radio buttons and comments field. Submit and confirm toast appears.

