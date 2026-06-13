# English translations for claude-fleet-starter installer.

# ── Pre-flight ────────────────────────────────────────────────────────────────
T_HEADER="
╭─────────────────────────────────────────────────────╮
│  claude-fleet-starter                               │
│                                                     │
│  Turnkey kit to install Claude Code and orchestrate │
│  multiple Claude Code instances across machines.    │
╰─────────────────────────────────────────────────────╯
"

T_OS_DETECTED="✓ Detected operating system: %s"
T_CHECKING_DEPS="Checking basic dependencies (curl, bash, etc.)..."
T_DEPS_MISSING="Missing basic tools. Read the error message above to know what to install."

# ── Claude Code ───────────────────────────────────────────────────────────────
T_CLAUDE_FOUND="✓ Claude Code is already installed (version: %s)"
T_INSTALL_CLAUDE="Do you want me to install Claude Code now?"
T_INSTALLING_CLAUDE="Installing Claude Code..."
T_CLAUDE_INSTALLED="✓ Claude Code installed. You can launch it with the command: claude"
T_CLAUDE_SKIPPED="OK, skipping Claude Code install. You can do it later with: curl -fsSL https://claude.ai/install.sh | bash"

# ── Tailscale ─────────────────────────────────────────────────────────────────
T_TAILSCALE_WHAT="
Tailscale is a free service that creates a private network between your machines,
as if they were all plugged into the same Wi-Fi router at home. It's secure
(everything is encrypted), easy to install, and it's what lets your Claude Code
instances on different machines talk to each other.

You don't have to install Tailscale, but without it your Claude Code instances
will be isolated from each other (no multi-machine messaging, no shared brain
synchronization, etc.)."

T_TAILSCALE_FOUND="✓ Tailscale is already installed."

T_INSTALL_TAILSCALE="Do you want me to install Tailscale?"
T_INSTALLING_TAILSCALE="Installing Tailscale..."

T_TAILSCALE_AUTH_NEEDED="
Tailscale is installed but now needs to be connected to your account.

Copy this command, paste it into a terminal (could be this one), and press Enter:"

T_PRESS_ENTER_WHEN_DONE="When that's done, come back here and press Enter to continue..."

T_TAILSCALE_REMINDER="⚠ You didn't install Tailscale. Your Claude Code instances won't be able to talk to each other across machines."

# ── Remote Control ────────────────────────────────────────────────────────────
T_RC_WHAT="
Remote Control lets you pilot Claude Code from your phone (via the Claude app)
or from claude.ai in your browser. Handy to keep an eye on what Claude is doing
when you're away from your desk."

T_RC_SECURITY_WARNING="
⚠ Security note: if you share your claude.ai account with anyone else
(family, team…), they'll also be able to remote-control your Claude Code.
You can always disable Remote Control later if needed."

T_ENABLE_RC_AUTOSTART="Do you want me to enable Remote Control at autostart?"

# ── Skills ────────────────────────────────────────────────────────────────────
T_SKILLS_QUESTION="I'll install the tools (skills) that make the kit useful."

T_SKILLS_LIST="
Included tools:

  • tailnet-messaging   — send/receive messages and files between your machines
  • claude-state-agent  — local server exposing Claude Code state
  • claude-launcher     — auto-launch Claude Code at boot
  • cerveau (brain)     — shared second brain (notes, patterns, decisions)
  • tailscale-secure-form — temporary web page to exchange secrets safely
  • skills-autoupdate   — auto-updates these tools every night
  • onboard-tailnet-machine — analyzes a machine and generates its CLAUDE.md
  • claude-on-remote    — start/control remote Claude Code via Tailscale SSH

You can disable any of these later."

T_INSTALLING_SKILL="• Installing %s..."

# ── Memory ────────────────────────────────────────────────────────────────────
T_INSTALL_MEMORY_STARTER="Do you want me to install 3-4 starter memories (generic security rules and best practices)?"
T_MEMORY_INSTALLED="✓ Starter memories installed in ~/.claude/projects/.../memory/"

# ── Bootstrap from history ────────────────────────────────────────────────────
T_BOOTSTRAP_QUESTION="Have you already used Claude Cowork, Claude Code, ChatGPT, etc.?"

T_BOOTSTRAP_WHAT="
If yes, I can analyze your past conversations to automatically generate your
CLAUDE.md file (= identity card of your machine: what you do, how you like to
work with AI, etc.). Big time saver: Claude Code will start with your context
already loaded."

T_BOOTSTRAP_HAS_HISTORY="Do you have a folder with that history?"

T_BOOTSTRAP_PATH_PROMPT="OK. Give me the folder path (e.g. /home/you/Documents/claude-history):"

T_BOOTSTRAP_PATH_INVALID="⚠ Path %s does not exist, skipping."

T_BOOTSTRAP_RUNNING="Bootstrap will run on your first Claude Code launch."

T_BOOTSTRAP_INSTRUCTIONS="
When you launch Claude Code for the first time, tell it:

  Analyze my history in %s and generate my CLAUDE.md following the
  instructions in bootstrap/analyze-history.md.

It'll do the rest."

# ── Done ──────────────────────────────────────────────────────────────────────
T_DONE_BANNER="
╭─────────────────────────────────────────────────────╮
│  ✓ Installation complete                            │
╰─────────────────────────────────────────────────────╯
"

T_NEXT_STEPS="Next steps:"
T_DOCS="📖 Documentation and help:"
T_SETTING_UP_RC_AUTOSTART="Setting up Remote Control autostart..."
