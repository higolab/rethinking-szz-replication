This repository contains a bug that was introduced at some point in the past
and later fixed. Below is the bug-fixing commit information.

Your task is to identify the commit(s) that introduced the bug, and explain
your reasoning.

[Bug-Fixing Commit]
- Commit hash: b594b55d7a3aa6334e558b0d6f2ce440a1047d87
- Commit message: 
- Diff:
```
commit b594b55d7a3aa6334e558b0d6f2ce440a1047d87
Author: Simon Marti <simon@ceilingcat.ch>
Date:   Thu Aug 4 19:24:09 2011 +0200
---
 src/simpleserver/CommandParser.java                |  9 ---------
 src/simpleserver/Server.java                       |  2 --
 src/simpleserver/command/AbstractCommand.java      | 22 ++++++----------------
 src/simpleserver/command/InvalidCommand.java       |  4 ++--
 .../command/OnlinePlayerArgCommand.java            | 10 ++--------
 src/simpleserver/command/PlayerArgCommand.java     | 10 ++--------
 6 files changed, 12 insertions(+), 45 deletions(-)

diff --git a/src/simpleserver/CommandParser.java b/src/simpleserver/CommandParser.java
index 59b6694..42cfffa 100644
--- a/src/simpleserver/CommandParser.java
+++ b/src/simpleserver/CommandParser.java
@@ -142,13 +142,4 @@ public class CommandParser {
       commandClasses.put(command.getClass(), command);
     }
   }
-
-  public void reload() {
-    for (ServerCommand serverCommand : serverCommands.values()) {
-      ((AbstractCommand) serverCommand).reloadText();
-    }
-    for (PlayerCommand playerCommand : playerCommands.values()) {
-      ((AbstractCommand) playerCommand).reloadText();
-    }
-  }
 }
diff --git a/src/simpleserver/Server.java b/src/simpleserver/Server.java
index 914f9a4..36382cc 100644
--- a/src/simpleserver/Server.java
+++ b/src/simpleserver/Server.java
@@ -240,8 +240,6 @@ public class Server {
     }
 
     addressFactory.toggle(!options.getBoolean("disableAddressFactory"));
-
-    commandParser.reload();
   }
 
   public void saveResources() {
diff --git a/src/simpleserver/command/AbstractCommand.java b/src/simpleserver/command/AbstractCommand.java
index 04a3fcd..3f33845 100644
--- a/src/simpleserver/command/AbstractCommand.java
+++ b/src/simpleserver/command/AbstractCommand.java
@@ -30,20 +30,18 @@ import simpleserver.Server;
 
 public abstract class AbstractCommand implements Command {
   protected final String name;
+  protected final String help;
   protected final String commandCode;
-  protected String helpText;
   protected CommandParser parser;
 
   protected AbstractCommand(String name, String commandCode) {
-    if (name != null) {
-      helpText = name + Color.WHITE + " : " + t(commandCode);
+    help = name;
 
+    if (name != null) {
       int splitIndex = name.indexOf(" ");
       if (splitIndex != -1) {
         name = name.substring(0, splitIndex);
       }
-    } else {
-      helpText = t(commandCode);
     }
 
     this.name = name;
@@ -55,10 +53,10 @@ public abstract class AbstractCommand implements Command {
   }
 
   public String getHelpText(String prefix) {
-    if (name != null) {
-      return Color.DARK_GREEN + prefix + helpText;
+    if (help != null) {
+      return Color.DARK_GREEN + prefix + help + " : " + Color.WHITE + t(commandCode);
     } else {
-      return helpText;
+      return t(commandCode);
     }
   }
 
@@ -124,14 +122,6 @@ public abstract class AbstractCommand implements Command {
     return string.toString();
   }
 
-  public void reloadText() {
-    if (name != null) {
-      helpText = name + Color.WHITE + " : " + t(commandCode);
-    } else {
-      helpText = t(commandCode);
-    }
-  }
-
   public void setParser(CommandParser parser) {
     this.parser = parser;
   }
diff --git a/src/simpleserver/command/InvalidCommand.java b/src/simpleserver/command/InvalidCommand.java
index c06a75f..fccd677 100644
--- a/src/simpleserver/command/InvalidCommand.java
+++ b/src/simpleserver/command/InvalidCommand.java
@@ -43,7 +43,7 @@ public class InvalidCommand extends AbstractCommand implements PlayerCommand,
   }
 
   @Override
-  public void reloadText() {
-    helpText = Color.RED + t(commandCode);
+  public String getHelpText(String prefix) {
+    return Color.RED + t(commandCode);
   }
 }
diff --git a/src/simpleserver/command/OnlinePlayerArgCommand.java b/src/simpleserver/command/OnlinePlayerArgCommand.java
index 60a5320..ab5b6b8 100644
--- a/src/simpleserver/command/OnlinePlayerArgCommand.java
+++ b/src/simpleserver/command/OnlinePlayerArgCommand.java
@@ -66,13 +66,7 @@ public abstract class OnlinePlayerArgCommand extends AbstractCommand implements
   }
 
   @Override
-  public void reloadText() {
-    if (name != null) {
-      helpText = name + Color.WHITE + " : " + t(commandCode) + " "
-          + t("(case-insensitive, name prefix works for online players)");
-    } else {
-      helpText = t(commandCode) + " "
-          + t("(case-insensitive, name prefix works for online players)");
-    }
+  public String getHelpText(String prefix) {
+    return super.getHelpText(prefix) + " " + t("(case-insensitive, name prefix works for online players)");
   }
 }
diff --git a/src/simpleserver/command/PlayerArgCommand.java b/src/simpleserver/command/PlayerArgCommand.java
index 3e92e40..349e33c 100644
--- a/src/simpleserver/command/PlayerArgCommand.java
+++ b/src/simpleserver/command/PlayerArgCommand.java
@@ -53,13 +53,7 @@ public abstract class PlayerArgCommand extends AbstractCommand implements
   }
 
   @Override
-  public void reloadText() {
-    if (name != null) {
-      helpText = name + Color.WHITE + " : " + t(commandCode) + " "
-          + t("(case-insensitive, name prefix works for online players)");
-    } else {
-      helpText = t(commandCode) + " "
-          + t("(case-insensitive, name prefix works for online players)");
-    }
+  public String getHelpText(String prefix) {
+    return super.getHelpText(prefix) + " " + t("(case-insensitive, name prefix works for online players)");
   }
 }
```

Investigate the repository using local tools. Do not use web search.

When you have identified the bug-introducing commit(s), conclude your
response with the following two sections:

## Bug-Introducing Commits
BIC: <hash1>, <hash2>, ... (or "BIC: NONE")

## Reasoning
Explain:
(1) How you investigated and what led you to this candidate.
(2) What specific change in this commit you believe introduced the bug.
(3) What evidence in the repository supports this conclusion.

Be honest about uncertainty if any.
