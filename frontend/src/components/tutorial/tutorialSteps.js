export function getTutorialSteps(role) {
  if (role === 'teacher') {
    return [
      {
        badge: 'Welcome',
        place: 'center',
        title: 'Welcome, coach ✋',
        body: "Show of Hands turns your class into a team. Here's how to set up your sections, assign quests, and spot who needs help — in about 30 seconds.",
      },
      {
        badge: 'Step 1',
        target: 'nav-sections',
        place: 'right',
        title: 'Create your sections',
        body: 'Spin up a section for each class period, set its capacity, and share the join code so students can enroll.',
      },
      {
        badge: 'Step 2',
        target: 'nav-quests',
        place: 'right',
        title: 'Assign quests',
        body: 'Build academic or social quests, set point values, and target the whole class or a single student who needs a nudge.',
      },
      {
        badge: 'Step 3',
        target: 'widget-teacher',
        place: 'right',
        title: 'Spot what needs attention',
        body: 'Each section card flags pending join requests and ungraded work, so nothing slips through the cracks.',
      },
      {
        badge: "You're set!",
        place: 'center',
        title: 'Ready to set up class?',
        body: 'Replay this anytime from your Profile. Let’s start with your sections.',
        cta: 'Browse sections',
      },
    ]
  }

  if (role === 'admin') {
    return [
      {
        badge: 'Welcome',
        place: 'center',
        title: 'Welcome to the console ✋',
        body: 'You keep the whole school running. This quick tour shows where to approve accounts, manage sections, and read school-wide stats.',
      },
      {
        badge: 'Step 1',
        target: 'nav-overview',
        place: 'right',
        title: 'Your command center',
        body: 'The overview surfaces everything that needs you today, plus school-wide stats at a glance.',
      },
      {
        badge: 'Step 2',
        target: 'nav-inbox',
        place: 'right',
        title: 'Approve new accounts',
        body: "Teachers and admins can't log in until you verify them. New class requests land in the Inbox too.",
      },
      {
        badge: 'Step 3',
        target: 'nav-sections',
        place: 'right',
        title: 'Manage every section',
        body: 'Reassign teachers, change a section’s status, or archive it — across the whole school.',
      },
      {
        badge: 'Step 4',
        target: 'nav-users',
        place: 'right',
        title: 'The user directory',
        body: 'Browse and manage every student, teacher, and admin account in your school.',
      },
      {
        badge: "You're set!",
        place: 'center',
        title: 'Ready to run the show?',
        body: 'Replay this anytime from your Profile. Let’s start with your sections.',
        cta: 'Browse sections',
      },
    ]
  }

  return [
    {
      badge: 'Welcome',
      place: 'center',
      title: 'Welcome to Show of Hands ✋',
      body: "Learning's better together. This quick tour shows how to earn points, get help, and team up with classmates. Takes about 30 seconds.",
    },
    {
      badge: 'Step 1',
      target: 'nav-sections',
      place: 'right',
      title: 'Join your classes',
      body: 'Every class you’re in lives under My sections. Tap “+ join section” and enter the code from your teacher.',
    },
    {
      badge: 'Step 2',
      target: 'nav-assignments',
      place: 'right',
      title: 'Stay on top of your work',
      body: 'Every assignment you owe lands here, with its due date front and center. Submit before the clock runs out to keep your grade — and your points — safe.',
    },
    {
      badge: 'Step 3',
      target: 'nav-quests',
      place: 'right',
      title: 'Take on quests',
      body: 'Quests are fun tasks — read for an hour, form a study group, hit the library. Finish them to rack up XP.',
    },
    {
      badge: 'Step 4',
      target: 'nav-bulletin',
      place: 'right',
      title: 'Ask for help, anonymously',
      body: 'Stuck? Post to the bulletin board with no name attached. A classmate jumps in — and you both earn points.',
    },
    {
      badge: 'Step 5',
      target: 'nav-rooms',
      place: 'right',
      title: 'Team up in study rooms',
      body: 'Accept a request and you drop into a study room with a live timer and chat. Beat the clock together.',
    },
    {
      badge: 'Step 6',
      target: 'topbar-points',
      place: 'below',
      title: 'Watch your points climb',
      body: 'Points stack up from quests and helping out. Check the leaderboard under Points to see where you rank.',
    },
    {
      badge: "You're set!",
      place: 'center',
      title: 'Ready to dive in?',
      body: 'You can replay this anytime from your Profile. Let’s find a class to join.',
      cta: 'Browse sections',
    },
  ]
}
