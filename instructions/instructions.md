## 1. Bot Overview

This Telegram bot is for friends who like Formula 1.  
The bot lets everyone place **virtual bets** on the **top 3 drivers** before each race.  

The bot:
- Reminds users when it is time to bet.
- Lets users choose who will be 1st, 2nd, and 3rd.
- Gives points after the race.
- Shows a leaderboard with total points for the season.  

One or more users are **admins**. Admins add races, set race dates and times, and enter the top 3 finishers after each race.

---

## 2. Main Goals

1. Let users place a bet on the top 3 drivers for each race.
2. Remind users to place a bet 2 hours before the race starts.
3. Let admins manage the race list (add races, edit times).
4. Let admins enter real race results (top 3).
5. Automatically calculate points for each user based on the rules.
6. Keep a season leaderboard with total points.
7. Let users see their own points and their past bets.
8. Work in both private chats and group chats.

---

## 3. User Stories (US-001, US-002, …)

### Player stories

- **US-001**  
  As a player, I want to start the bot and see a short help text so that I understand what it can do.

- **US-002**  
  As a player, I want to get a reminder before each race so that I don’t forget to place my bet.

- **US-003**  
  As a player, I want to place a bet on the top 3 drivers for a race so that I can play the game with my friends.

- **US-004**  
  As a player, I want to pick drivers from a list, not type their names, so that I don’t make spelling mistakes.

- **US-005**  
  As a player, I want to change my bet before the race starts so that I can fix mistakes or change my mind.

- **US-006**  
  As a player, I want to see my bets for a race so that I remember what I picked.

- **US-007**  
  As a player, I want to see my total points so that I know how well I am doing.

- **US-008**  
  As a player, I want to see a leaderboard so that I can compare my points with my friends.

### Admin stories

- **US-009**  
  As an admin, I want to upload or add a list of races with dates and start times so that reminders can go out automatically.

- **US-010**  
  As an admin, I want to edit race info (time, date, name) so that I can fix mistakes.

- **US-011**  
  As an admin, I want to enter race results (top 3 drivers) so that the bot can give points.

- **US-012**  
  As an admin, I want the bot to calculate points for all users automatically so that I don’t have to do it by hand.

- **US-013**  
  As an admin, I want to see a list of bets for a race so that I can check that everything looks right.

- **US-014**  
  As an admin, I want to reopen or close betting manually if needed so that I can handle special cases (delays, time changes, etc.).

- **US-015**  
  As an admin, I want to see logs or summaries per race (who got how many points) so that I can share them with the group.

---

## 4. Features (F-001, F-002, …)

### F-001 – Start and Help

- **What it does**  
  Shows a welcome message and a simple help text. Explains what the bot is and lists main commands.

- **How the user starts it**  
  - Command `/start`  
  - Command `/help`

- **What happens if something goes wrong**  
  - If anything fails, show a simple message:  
    > “Sorry, something went wrong. Please try again with /start.”

---

### F-002 – Player Registration

- **What it does**  
  Creates or updates a player record when they first use the bot. Saves their Telegram user ID and display name.

- **How the user starts it**  
  - Automatically when they send `/start` or any valid command for the first time.

- **What happens if something goes wrong**  
  - If saving the user fails, show:  
    > “I could not save your profile. Please try again later.”

---

### F-003 – Race List Management (Admin)

- **What it does**  
  Lets admins add, view, and edit races.  
  Each race has:
  - Race ID (internal)
  - Race name (e.g., “Bahrain Grand Prix”)
  - Date and start time
  - Status: upcoming / finished
  - Flag if reminder was sent

- **How the user starts it**  
  - Command `/admin_races` (only admins)
  - Option to:
    1. Add race
    2. Edit race
    3. Delete race
    4. View all races

- **What happens if something goes wrong**  
  - If user is not admin:  
    > “You are not allowed to do this. Ask an admin for help.”
  - If race not found:  
    > “I cannot find this race. Please check the ID.”
  - If date/time is in wrong format:  
    > “I don’t understand this date or time. Please use the shown format.”

---

### F-004 – Upload Race Calendar (Admin)

- **What it does**  
  Lets admin upload a full list of races at once. For example, as a text format or a simple CSV-style message:
  - One line per race: `Race Name;YYYY-MM-DD;HH:MM`

- **How the user starts it**  
  - Command `/upload_races` (only admins)
  - Bot asks admin to send text or file in a specific simple format.

- **What happens if something goes wrong**  
  - If parsing fails for some lines:
    - Show which lines had errors.
    - Save only valid lines.
    - Example message:  
      > “I added 20 races. 2 lines had errors and were skipped.”

---

### F-005 – Betting Flow (Place a Bet)

- **What it does**  
  Lets players place a bet for a race:
  - Choose race (if more than one upcoming race is open).
  - Choose 1st place driver.
  - Choose 2nd place driver.
  - Choose 3rd place driver.
  - Confirm bet.

- **How the user starts it**  
  - Command `/bet`
  - Or by pressing a **“Place bet”** button in a reminder message.

- **How it works (UI idea)**  
  1. Bot shows list of open races (buttons).
  2. User picks race.
  3. Bot shows driver list as buttons for **1st place**.
  4. User picks driver for 1st place.
  5. Bot shows driver list again for **2nd place** (without the chosen first driver, if possible).
  6. User picks driver for 2nd place.
  7. Bot shows driver list again for **3rd place** (without chosen first and second drivers).
  8. Bot shows a summary:  
     > “Your bet for [Race Name]: 1) VER, 2) PIA, 3) NOR. Confirm?”  
     Buttons: [Confirm] [Cancel]

- **What happens if something goes wrong**  
  - If race is already started or closed:  
    > “Betting for this race is closed.”
  - If user tries to bet twice:
    - Option 1: overwrite previous bet after confirmation.
    - Message:  
      > “You already have a bet for this race. Do you want to replace it?”
  - If driver list fails to load:  
    > “I cannot load the driver list. Please try again later.”

---

### F-006 – Edit or Delete Bet (Before Start)

- **What it does**  
  Lets players change or remove their bet for a race before betting closes (e.g., race start time minus 5–10 minutes).

- **How the user starts it**  
  - Command `/my_bets`
  - Bot shows list of upcoming races with existing bets and options:
    - [Change bet]
    - [Delete bet]

- **What happens if something goes wrong**  
  - If betting is already closed:  
    > “You cannot change this bet. Betting is closed for this race.”
  - If no bet exists:  
    > “You don’t have a bet for this race.”

---

### F-007 – Enter Race Results (Admin)

- **What it does**  
  Lets admin enter top 3 real results for a race:
  - 1st, 2nd, 3rd drivers (chosen from driver list).

  After saving:
  - Bot calculates points for every bet for that race.
  - Bot updates the leaderboard.

- **How the user starts it**  
  - Command `/results`
  - Bot shows list of races without results (buttons).
  - Admin picks race and then picks 1st, 2nd, 3rd drivers from lists.

- **Scoring rules**  
  - 3 points: guessed driver and exact position.  
  - 1 point: guessed driver but wrong position (still in top 3).  
  - Total = sum of all points for that race.

- **What happens if something goes wrong**  
  - If results already set:
    - Ask admin if they want to overwrite.
  - If user is not admin:
    > “You are not allowed to set results.”
  - If score calculation fails:
    > “I could not calculate scores. Please try again later or contact the admin.”

---

### F-008 – Leaderboard

- **What it does**  
  Shows a list of players with their total points for all races.  
  Example format:

  1. Alice – 45 points  
  2. Bob – 41 points  
  3. Charlie – 30 points  

- **How the user starts it**  
  - Command `/leaderboard`

- **What happens if something goes wrong**  
  - If no data yet:  
    > “No points yet. Play your first race to see the leaderboard.”

---

### F-009 – My Stats and History

- **What it does**  
  Shows:
  - Total points for the user.
  - Number of races they bet on.
  - Short history (last N races: race name, bet, points from that race).

- **How the user starts it**  
  - Command `/me` or `/mystats`

- **What happens if something goes wrong**  
  - If user has no bets:  
    > “You don’t have any bets yet. Use /bet to place your first bet.”

---

### F-010 – Reminders and Notifications

- **What it does**  
  Sends a message 2 hours before each race start to:
  - A group chat (if bot is added there and allowed).
  - Or to each user who enabled personal reminders (optional extra setting).

  Message example:  
  > “🏁 It’s time to place your bet for [Race Name]! Use /bet or tap the button below.”  
  With a [Place bet] button.

- **How it starts**  
  - By schedule, based on race time stored in data.
  - Internally, this will need a scheduler (cron, job, etc.), but in simple words we just say: “The bot checks times regularly and sends reminders.”

- **What happens if something goes wrong**  
  - If a reminder fails to send to some users, it still tries for others.
  - If there are no upcoming races: no reminders.

---

### F-011 – Admin Access Control

- **What it does**  
  Makes sure only specific users can use admin commands.

- **How it starts**  
  - Bot uses a simple list of admin user IDs in config or database.

- **What happens if something goes wrong**  
  - Non-admins see:
    > “You are not allowed to use this command.”

---

## 5. Conversations & Commands (C-001, C-002, …)

### C-001 – Start / Help Flow

- **User sends**  
  `/start` or `/help`

- **Bot replies with**  
  - Short welcome text:
    > “Hi! I’m an F1 betting bot. I help you place virtual bets on the top 3 drivers for each race.”
  - Short list of main commands:
    - `/bet` – place or change a bet
    - `/my_bets` – see your current bets
    - `/leaderboard` – see top players
    - `/me` – see your points
  - If user is admin, show extra admin commands list.

- **How user moves to next step**  
  - They choose a command from the list or type it.

---

### C-002 – Place Bet Flow

- **User sends**  
  `/bet`  
  or presses [Place bet] button from reminder.

- **Bot replies with**  
  1. If there are multiple open races:
     - Shows a list of race buttons:  
       `[Race 1] [Race 2] [Race 3]`
  2. After user picks race:
     - Shows driver list for 1st place.
  3. After user picks 1st place:
     - Shows driver list for 2nd place.
  4. After user picks 2nd place:
     - Shows driver list for 3rd place.
  5. Shows summary and asks to confirm.

- **How user moves to next step**  
  - Clicks buttons for race and drivers.
  - Clicks [Confirm] at the end to save the bet.

---

### C-003 – My Bets Flow

- **User sends**  
  `/my_bets`

- **Bot replies with**  
  - List of upcoming races where user has bets. Example:

    > “Your bets:  
    > – Bahrain GP: 1 VER, 2 PIA, 3 NOR [Change] [Delete]  
    > – Jeddah GP: 1 LEC, 2 VER, 3 RUS [Change] [Delete]”

- **How user moves to next step**  
  - Clicks [Change] to go into bet flow again (C-002) for that race.  
  - Clicks [Delete] to remove the bet (with a “Are you sure?” confirmation).

---

### C-004 – Leaderboard Flow

- **User sends**  
  `/leaderboard`

- **Bot replies with**  
  - A simple sorted list of players with total points.
  - Optional button [Show more] if list is long.

- **How user moves to next step**  
  - Can tap [Show more] to see more places.
  - Or just stop.

---

### C-005 – My Stats Flow

- **User sends**  
  `/me` or `/mystats`

- **Bot replies with**  
  - Short summary:
    > “You have 34 points from 5 races.  
    > Last race (Bahrain): bet 1 VER, 2 PIA, 3 NOR – you earned 4 points.”

- **How user moves to next step**  
  - They can use other commands or stop.

---

### C-006 – Admin Race Management Flow

- **User sends**  
  `/admin_races` (admin only)

- **Bot replies with**  
  - A menu with buttons:
    - [View races]
    - [Add race]
    - [Edit race]
    - [Delete race]

- **How user moves to next step**  
  - Tap a button and follow simple questions:
    - Add race: ask for race name, date, time.
    - Edit race: pick a race, then choose what to change.
    - Delete race: pick a race and confirm.

---

### C-007 – Admin Upload Races Flow

- **User sends**  
  `/upload_races` (admin only)

- **Bot replies with**  
  - Text instructions on format.
  - Example:

    > “Please send a text with one race per line, like:  
    > Bahrain Grand Prix;2025-03-02;16:00”

- **How user moves to next step**  
  - Admin sends text or file.
  - Bot parses and reports success and errors.

---

### C-008 – Admin Enter Results Flow

- **User sends**  
  `/results` (admin only)

- **Bot replies with**  
  1. List of races without results.
  2. After race chosen:
     - Ask to pick 1st place driver.
     - Ask to pick 2nd place driver.
     - Ask to pick 3rd place driver.
  3. Show summary and ask to confirm.
  4. After confirm, calculate scores and show short summary (top players and their race points).

- **How user moves to next step**  
  - Clicking driver buttons and [Confirm].

---

## 6. Data (D-001, D-002, …)

- **D-001 – Users**  
  - Telegram user ID  
  - Name / username  
  - Is admin (yes/no)  
  - Settings (like “wants direct reminders” yes/no – optional)

- **D-002 – Drivers List**  
  - Driver code (e.g., VER, LEC, HAM)  
  - Full name  
  - Active flag (for season list)

- **D-003 – Races**  
  - Race ID  
  - Race name  
  - Date  
  - Start time  
  - Timezone (simple, one main timezone for now)  
  - Status (upcoming / finished)  
  - Reminder sent (yes/no)

- **D-004 – Bets**  
  - User ID  
  - Race ID  
  - Driver for 1st place  
  - Driver for 2nd place  
  - Driver for 3rd place  
  - Created time  
  - Updated time

- **D-005 – Race Results**  
  - Race ID  
  - Driver for 1st place  
  - Driver for 2nd place  
  - Driver for 3rd place  
  - Time when results were saved

- **D-006 – Points Per Race**  
  - User ID  
  - Race ID  
  - Points for that race

- **D-007 – Leaderboard (Totals)**  
  - User ID  
  - Total points across all races

- **D-008 – Bot Settings** (optional)  
  - List of admin IDs  
  - Bet closing offset (e.g., 5 minutes before race)  
  - Default timezone

---

## 7. Extra Details

1. **Database or in-memory?**  
   - The bot should use a **simple database** (for example, SQLite or any small DB).  
   - It should not keep everything only in memory, because:
     - Races and bets must stay after bot restart.
     - We need a history for the whole season.

2. **External API or website?**  
   - Minimum version: no external API.  
     - Admin adds races and results by hand.  
   - Future version (optional): use an F1 API to:
     - Load race calendar.
     - Load race results automatically.

3. **Remember users between sessions?**  
   - Yes.  
   - The bot must remember users, bets, and points even if:
     - The bot restarts.
     - The user closes Telegram and comes back later.

4. **Error messages**  
   - Simple and clear.  
   - Say what went wrong and what to do next.  
   - Examples:
     - “I don’t understand this date. Please use YYYY-MM-DD.”
     - “Betting is closed for this race.”
     - “You don’t have any bets yet.”

5. **Limits**  
   - Max drivers in list: enough for full F1 grid (now ~20), but can be up to 30 in data.  
   - Each user can have only **one** bet per race.  
   - Bets can be changed only **before** betting closes.  
   - Number of races: should handle at least one full season (20–25 races).

6. **Group vs private chats**  
   - The bot should work:
     - In a group chat (main use for friends together).
     - In private messages (optional extra).  
   - In group chat:
     - Leaderboard and reminders are posted into the group.
   - In private chat:
     - User can get personal reminders (optional).

7. **Time zones**  
   - To keep it simple:
     - Bot uses **one main timezone** (set by admin).
     - All race times and reminders use this timezone.

---

## 8. Build Steps (B-001, B-002, …)

**B-001 – Create basic bot and commands**

- Set up the bot token and connection to Telegram.
- Implement `/start` and `/help` (C-001) using **F-001**.
- When `/start` is used, create user record (**D-001**, **F-002**).

---

**B-002 – Set up database and data models**

- Create tables or structures for:
  - Users (**D-001**)
  - Drivers (**D-002**)
  - Races (**D-003**)
- Fill driver list for the season (manual seed data).

---

**B-003 – Admin access control**

- Add a simple list of admin IDs in config or in **D-008**.
- Before running admin commands, check **F-011**.

---

**B-004 – Race management for admins**

- Implement `/admin_races` flow (C-006) with **F-003**:
  - Add race
  - View races
  - Edit race
  - Delete race
- Save race data in **D-003**.

---

**B-005 – Optional: upload race calendar**

- Implement `/upload_races` flow (C-007) with **F-004**.
- Parse simple text format and save multiple races to **D-003**.

---

**B-006 – Betting system**

- Implement `/bet` command and “Place bet” button flow (C-002) using **F-005**.
- Save bets into **D-004**.
- Add logic to check if betting is still open based on race time (**D-003**, **D-008**).

---

**B-007 – Manage my bets**

- Implement `/my_bets` flow (C-003) using **F-006**.
- Allow changing and deleting bets before betting closes.
- Update **D-004** when user changes a bet.

---

**B-008 – Enter results and scoring**

- Implement `/results` flow (C-008) with **F-007**.
- Save results in **D-005**.
- After saving results:
  - For each bet in **D-004** for that race:
    - Calculate points using scoring rules.
    - Save points in **D-006**.
  - Update totals in **D-007** (leaderboard).

---

**B-009 – Leaderboard and stats**

- Implement `/leaderboard` (C-004) using **F-008**, reading from **D-007**.
- Implement `/me` or `/mystats` (C-005) using **F-009**, reading from **D-006** and **D-004**.

---

**B-010 – Reminders**

- Add a simple scheduler (in code) that:
  - Regularly checks races in **D-003**.
  - For races happening in 2 hours, sends reminder messages using **F-010**.
- Include [Place bet] button that opens **C-002**.

---

**B-011 – Polish and safety**

- Add clear error messages as described in section 7.
- Handle edge cases:
  - No upcoming races.
  - Results already set.
  - User tries to bet on finished race.
- Test flows in:
  - Private chat.
  - Group chat.
