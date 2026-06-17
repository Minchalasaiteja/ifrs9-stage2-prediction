# 🎯 SICRSense UI/UX Integration - Visual Navigation Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         🏠 LANDING PAGE (/)                                │
│                           index_v1.html                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  [🧠 SICRSense Logo - clickable] [🌙 THEME TOGGLE] [≡ MENU]       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  HERO SECTION:                                                              │
│  "Predict SICR with Bank-Grade Precision"                                 │
│                                                                              │
│  [Start Free Trial] [Simulate Risk] [View Workflow] ← NEW BUTTON          │
│      ↓                                     ↓                              │
│     /signup                          /ifrs9-workflow                     │
│      │                                     │                              │
│      │                                     └────────────────────┐         │
│      │                                                          │         │
│  ─────────────────────────────────────────────────────────┐     │         │
│  │                                                         │     │         │
│  │ [✓] Features Section                                   │     │         │
│  │ [✓] Workflow Demo                                      │     │         │
│  │ [✓] Live Interactive Demo                             │     │         │
│  │                                                         │     │         │
│  │ Footer: [Back to Home]                                 │     │         │
│  └─────────────────────────────────────────────────────────┘     │         │
│                                                                    │         │
└────────────────────────────────────────────────────────────────────┼─────────┘
                                                                      │
                        ┌─────────────────────┬─────────────────────┘
                        │                     │
                        ▼                     ▼
            ┌─────────────────────┐  ┌──────────────────────────┐
            │  🔐 LOGIN (/login)  │  │  📝 SIGNUP (/signup)    │
            │ login_v1.html       │  │ signup_v1.html         │
            └─────────────────────┘  └──────────────────────────┘
            │                         │
            │ ┌─────────────────────┐ │ ┌──────────────────────────┐
            │ │ [🧠 Logo] ← home   │ │ │ [🧠 Logo] ← home       │
            │ │ [🌙 Toggle]        │ │ │ [🌙 Toggle]            │
            │ │                     │ │ │                        │
            │ │ Sign In Form        │ │ │ Multi-Step Form        │
            │ │ ─────────────────   │ │ │ ───────────────────    │
            │ │ Email:    [_____]  │ │ │ Step 1/2/3 Indicator   │
            │ │ Password: [_____]  │ │ │ Name:     [_____]      │
            │ │ [2FA]             │ │ │ Email:    [_____]      │
            │ │ [Social Login]    │ │ │ Company:  [_____]      │
            │ │                     │ │ │                        │
            │ │ [Sign In Button]  │ │ │ [Next] [Previous]      │
            │ │                     │ │ │                        │
            │ │ Sign Up? ────────┐ │ │ │ Account? ──────┐      │
            │ │  [Sign up]       │ │ │ │  [Sign in]     │      │
            │ │   ↓              │ │ │ │    ↓           │      │
            │ │  /signup ────────┼─┼─┼─→ /login        │      │
            │ │                  │ │ │ │                │      │
            │ │ Forgot password: │ │ │ │                │      │
            │ │  [Reset link]    │ │ │ │                │      │
            │ │                  │ │ │ │                │      │
            │ │ Footer:          │ │ │ │ Footer:        │      │
            │ │ [Back to Home]   │ │ │ │ [Back to Home] │      │
            │ └─────────────────────┘ │ └──────────────────────────┘
            │                         │
            └─────────────────────────┘
                    │ (on login)
                    ▼
         ┌────────────────────────────────────┐
         │ 🎯 IFRS9 WORKFLOW (/ifrs9-workflow)│
         │   ifrs9_workflow_v1.html           │
         ├────────────────────────────────────┤
         │                                    │
         │ ┌──────────────────────────────┐  │
         │ │ [📊 IFRS 9 Workflow]  [🌙]  │  │  Fixed Header
         │ │ [Dashboard] [Home]          │  │
         │ └──────────────────────────────┘  │
         │                                    │
         │ ┌──────────────────────────────┐  │
         │ │ Hero Section                 │  │
         │ │ "Understanding Credit Risk   │  │
         │ │  Migration"                  │  │
         │ └──────────────────────────────┘  │
         │                                    │
         │ ┌──────────────────────────────┐  │
         │ │ IFRS 9 Stage Visualization  │  │
         │ │ [Stage 1] [Stage 2] [Stage 3]  │
         │ │ ┌────┐    ┌────┐    ┌────┐     │
         │ │ │    │ ──→ │    │ ──→ │    │  │
         │ │ └────┘    └────┘    └────┘     │
         │ │                                  │
         │ │ SICR Detection Workflow       │  │
         │ │ D3.js Visualizations         │  │
         │ │ Metrics Dashboard            │  │
         │ └──────────────────────────────┘  │
         │                                    │
         │ Navigation:                        │
         │ • [Dashboard] → /dashboard         │
         │ • [Home] → /                       │
         │ • Theme Toggle in header           │
         │                                    │
         └────────────────────────────────────┘
```

---

## 📋 Route Mapping

| URL | Template | Features | Auth Required |
|-----|----------|----------|----------------|
| `/` | `index_v1.html` | Landing, features, demo | ❌ No |
| `/login` | `auth/login_v1.html` | Login, 2FA, social auth | ❌ No |
| `/signup` | `auth/signup_v1.html` | Registration, multi-step | ❌ No |
| `/ifrs9-workflow` | `dashboard/ifrs9_workflow_v1.html` | IFRS 9 visualization | ✅ Yes |

---

## 🎨 Theme Management

```
Every Page:
┌─────────────────────────────────────────────┐
│ [🌙 THEME TOGGLE]                          │
│ Click toggles: Dark ↔ Light                │
│ Saves to: localStorage['sicrsense-theme']  │
│ Persists: Across all pages & refreshes     │
└─────────────────────────────────────────────┘

Dark Mode (Default):
- Background: #0a0a0f (near black)
- Text: #ffffff (white)
- Accent: #00f0ff (cyan)
- Mood: Professional, modern, tech

Light Mode:
- Background: #f8fafc (light gray)
- Text: #0f172a (dark blue)
- Accent: #0066cc (blue)
- Mood: Bright, clean, accessible
```

---

## ✅ Navigation Flows

### Flow 1: First-time User
```
Home (/) 
  → [Start Free Trial]
    → Signup (/signup)
      → [Enter Dashboard]
        → Success!
```

### Flow 2: Returning User
```
Home (/)
  → [Sign In] or navigate to /login
    → Login (/login)
      → [Sign In]
        → Dashboard or IFRS9 Workflow
```

### Flow 3: View IFRS9 Workflow
```
Home (/) 
  → [View Workflow]
    → IFRS9 Workflow (/ifrs9-workflow)
      → Requires login
      → Redirects to /login if not authenticated
```

### Flow 4: Between Auth Pages
```
Login ↔ Signup
  ↓      ↓
  └──→ Home (logo click)
       Footer click: [Back to Home]
```

---

## 🔐 Authentication Flow

```
Unauthenticated User:
  /ifrs9-workflow → [REDIRECT] → /login → [enter credentials]
                                    ↓
                              [login success]
                                    ↓
                          /ifrs9-workflow ✓

Authenticated User:
  /ifrs9-workflow → [ALLOWED] → displays workflow content
```

---

## 📱 Responsive Behavior

| Screen | Layout |
|--------|--------|
| Mobile | Single column, stacked navigation, large touch targets |
| Tablet | Optimized spacing, readable text |
| Desktop | Full-width, side-by-side layouts, hover effects |

---

## 🚀 Key Features

✨ **Per Page:**
- Dark/Light theme toggle
- Clickable logos return to home
- Footer links where applicable
- Mobile responsive

✨ **Navigation:**
- All pages interconnected
- Clear CTAs (Call-to-Actions)
- Breadcrumb awareness
- Protected routes where needed

✨ **Theme:**
- Instant switching
- Persistent across sessions
- Smooth color transitions
- Complete CSS variable coverage

---

## 💡 Testing Scenarios

### Scenario 1: Theme Persistence
1. Go to `/`
2. Toggle to light mode
3. Navigate to `/signup`
4. Verify still light mode ✓
5. Refresh page → Still light ✓

### Scenario 2: Complete User Journey
1. Start at `/` (dark mode)
2. Click "Start Free Trial" → goes to `/signup`
3. Fill form, submit
4. Redirected to dashboard
5. Click "View Workflow" → goes to `/ifrs9-workflow`
6. Toggle theme → light mode
7. Click "Home" in header → back to `/`
8. Verify light mode persists ✓

### Scenario 3: Returning User
1. Logout (session expired)
2. Try to access `/ifrs9-workflow`
3. Redirected to `/login`
4. Previous theme preference restored ✓
5. Login and access workflow

---

## 📊 Files Modified/Created

```
Modified:
├── app/main.py (4 routes updated)
├── templates/index_v1.html (added IFRS9 button)
├── templates/auth/login_v1.html (logo link, footer)
├── templates/auth/signup_v1.html (logo link, signup link, footer)
└── templates/dashboard/ifrs9_workflow_v1.html (added header nav)

Created:
├── static/js/theme-manager.js (utility class - optional)
└── INTEGRATION_COMPLETE.md (this documentation)
```

---

## 🎓 Implementation Notes

All v1 templates use **localStorage key: `'sicrsense-theme'`**

This ensures theme synchronization across:
- Page navigations
- Browser tabs (if on same domain)
- Browser closures and returns
- Different devices (if backend syncs)

---

**Status: ✅ COMPLETE & READY FOR PRODUCTION**

All redirections working | All navigation links functional | Theme persistence verified | Dark/Light mode seamless
