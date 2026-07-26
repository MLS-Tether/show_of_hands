export const ADMIN_NAV_GROUPS = [
  { label: null, items: [{ label: 'Overview', to: '/admin/overview', end: true, tour: 'nav-overview' }] },
  { label: 'Approvals', items: [{ label: 'Inbox', to: '/admin/inbox', badge: 'inbox', tour: 'nav-inbox' }] },
  {
    label: 'Manage',
    items: [
      { label: 'Sections', to: '/admin/sections', tour: 'nav-sections' },
      { label: 'Users', to: '/admin/users', tour: 'nav-users' },
    ],
  },
  { label: 'School', items: [{ label: 'Settings', to: '/admin/settings' }] },
]

export const APP_NAV_ITEMS = [
  { label: 'Dashboard', to: '/dashboard', end: true },
  { label: 'My sections', to: '/sections', tour: 'nav-sections' },
  { label: 'Assignments', to: '/assignments', studentOnly: true, tour: 'nav-assignments' },
  { label: 'Quests', to: '/quests', tour: 'nav-quests' },
  { label: 'Bulletin board', to: '/bulletin-board', studentOnly: true, tour: 'nav-bulletin' },
  { label: 'Study rooms', to: '/study-rooms', studentOnly: true, tour: 'nav-rooms' },
  { label: 'Points', to: '/points', studentOnly: true },
]
