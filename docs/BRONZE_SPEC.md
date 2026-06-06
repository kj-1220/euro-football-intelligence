# Bronze Layer Specification — Locked
## Euro Football Intelligence Platform
### `euro_raw` schema — Append-only, never alter

---

## Architectural Decisions (Locked)

### Data Tier Classification

**Tier A — Historical Record Data — No floor**
Results, standings, competition winners, trophy records.
These are facts, not metrics. A user asking "who won Champions League 20 years ago" is a valid question.
Sources: OpenFootball, football-data.org
Destination: Knowledge graph + RAG corpus

**Tier B — Contextual / Narrative Data — No floor**
Manager career records, club tenures, tactical evolution, transfer history.
Powers narrative reasoning and relationship context in the knowledge graph and RAG corpus.
Sources: Transfermarkt, FBref (deep scrape), manual curation
Destination: RAG corpus + knowledge graph edges only

**Tier C — Metric Data — 2021-22 floor**
xG, PPDA, progressive passes, all advanced stats, player per-90.
Post-COVID, post-tactical-paradigm-shift. Clean, consistent, comparable.
Predictive signals and dashboard metrics only use this window.
Sources: FBref (scraper), Understat
Destination: Full Bronze → Silver → Gold pipeline

### FBref Historical Exception
FBref scraper for Tier B contextual data (manager career records, club tactical history) has no hard floor.
FBref scraper for Tier C metric pipeline starts at 2021-22.
These are two separate ingestion patterns from the same source.

---

## Confirmed Data Sources

| Source | Tier | Access Method | Primary Use |
|---|---|---|---|
| football-data.org | A + partial C | REST API (free tier) | Fixtures, results, standings, lineups, events |
| StatsBomb Open Data | C | GitHub JSON files | Event-level tactical data, RAG corpus |
| OpenFootball | A | GitHub CSV/JSON files | Deep historical results, competition winners |
| FBref | B + C | Scraper (rate-limited) | xG, PPDA, pressing, all advanced metrics |
| Understat | C | Scraper | xG per match and player, 2014-present |
| Transfermarkt | B | Scraper | Transfers, valuations, manager tenure |
| ClubElo | A | Single REST endpoint | Historical Elo ratings, strength signal |
| API-Football | C (WC2026 only) | REST API | World Cup 2026 fixtures and coverage |

**Live data: not required.** Platform refreshes on a scheduled basis aligned with match schedules (approx. 2x per week during season).

---

## Competitions in Scope

### Phase 1 (Prototype)
- Premier League
- La Liga
- Bundesliga
- Serie A
- Ligue 1

### Phase 2
- UEFA Champions League
- UEFA Europa League
- Eredivisie
- Liga Portugal

### Special Module
- World Cup 2026 (`wc2026_raw` schema — separate from `euro_raw`)

---

## Bronze Tables

---

### REFERENCE TABLES
Shared across all sources. Everything joins to these.

---

#### `euro_raw.competitions`
```sql
competition_id        VARCHAR PRIMARY KEY,
competition_name      VARCHAR NOT NULL,
competition_code      VARCHAR,           -- e.g. PL, PD, BL1, SA, FL1
country               VARCHAR,
confederation         VARCHAR,           -- UEFA, CONMEBOL, etc.
tier                  INTEGER,           -- 1 = top flight
format                VARCHAR,           -- round_robin, cup, group_knockout
n_teams               INTEGER,
data_source           VARCHAR,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.clubs`
```sql
club_id               VARCHAR PRIMARY KEY,
club_name             VARCHAR NOT NULL,
club_short_name       VARCHAR,
club_tla              VARCHAR,           -- 3-letter abbreviation
competition_id        VARCHAR,           -- current primary competition
country               VARCHAR,
venue_id              VARCHAR,
founded_year          INTEGER,
data_source           VARCHAR,
source_club_id        VARCHAR,           -- source system ID for join/dedup
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.venues`
```sql
venue_id              VARCHAR PRIMARY KEY,
venue_name            VARCHAR NOT NULL,
city                  VARCHAR,
country               VARCHAR,
capacity              INTEGER,
surface               VARCHAR,           -- grass, artificial
latitude              NUMERIC(9,6),
longitude             NUMERIC(9,6),
elevation_ft          NUMERIC(8,2),
is_dome               BOOLEAN DEFAULT FALSE,
data_source           VARCHAR,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.players`
```sql
player_id             VARCHAR PRIMARY KEY,
player_name           VARCHAR NOT NULL,
nationality           VARCHAR,
date_of_birth         DATE,
position              VARCHAR,
foot                  VARCHAR,           -- right, left, both
current_club_id       VARCHAR,
data_source           VARCHAR,
source_player_id      VARCHAR,           -- source system ID for join/dedup
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

### FBREF TABLES — Tier C (2021-22 floor unless noted)

---

#### `euro_raw.fbref_team_standard_stats`
One row per club per season per competition.
```sql
id                    SERIAL PRIMARY KEY,
club_id               VARCHAR,
club_name             VARCHAR,
season                VARCHAR,           -- e.g. 2023-24
competition           VARCHAR,
matches_played        INTEGER,
wins                  INTEGER,
draws                 INTEGER,
losses                INTEGER,
goals_for             INTEGER,
goals_against         INTEGER,
goal_difference       INTEGER,
xg_for                NUMERIC(6,2),
xg_against            NUMERIC(6,2),
xg_difference         NUMERIC(6,2),
npxg_for              NUMERIC(6,2),
npxg_against          NUMERIC(6,2),
points                INTEGER,
points_per_game       NUMERIC(4,2),
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_team_shooting`
One row per club per season per competition.
```sql
id                    SERIAL PRIMARY KEY,
club_id               VARCHAR,
club_name             VARCHAR,
season                VARCHAR,
competition           VARCHAR,
shots                 INTEGER,
shots_on_target       INTEGER,
shots_on_target_pct   NUMERIC(5,2),
goals                 INTEGER,
xg                    NUMERIC(6,2),
npxg                  NUMERIC(6,2),
avg_shot_distance     NUMERIC(5,2),
shots_from_free_kicks INTEGER,
npxg_per_shot         NUMERIC(5,3),
goals_minus_xg        NUMERIC(6,2),
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_team_passing`
One row per club per season per competition.
```sql
id                    SERIAL PRIMARY KEY,
club_id               VARCHAR,
club_name             VARCHAR,
season                VARCHAR,
competition           VARCHAR,
passes_completed      INTEGER,
passes_attempted      INTEGER,
pass_completion_pct   NUMERIC(5,2),
progressive_passes    INTEGER,
key_passes            INTEGER,
passes_final_third    INTEGER,
passes_penalty_area   INTEGER,
crosses_penalty_area  INTEGER,
xa                    NUMERIC(6,2),
assisted_shots        INTEGER,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_team_defensive`
One row per club per season per competition. PPDA lives here.
```sql
id                    SERIAL PRIMARY KEY,
club_id               VARCHAR,
club_name             VARCHAR,
season                VARCHAR,
competition           VARCHAR,
tackles               INTEGER,
tackles_won           INTEGER,
pressures             INTEGER,
pressure_success_rate NUMERIC(5,2),
pressure_regains      INTEGER,
pressures_def_third   INTEGER,
pressures_mid_third   INTEGER,
pressures_att_third   INTEGER,
blocks                INTEGER,
interceptions         INTEGER,
clearances            INTEGER,
ppda                  NUMERIC(6,3),
ppda_allowed          NUMERIC(6,3),
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_team_possession`
One row per club per season per competition.
```sql
id                    SERIAL PRIMARY KEY,
club_id               VARCHAR,
club_name             VARCHAR,
season                VARCHAR,
competition           VARCHAR,
possession_pct        NUMERIC(5,2),
touches               INTEGER,
touches_def_third     INTEGER,
touches_mid_third     INTEGER,
touches_att_third     INTEGER,
progressive_carries   INTEGER,
carries_final_third   INTEGER,
carries_penalty_area  INTEGER,
miscontrols           INTEGER,
dispossessed          INTEGER,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_team_misc`
One row per club per season per competition.
```sql
id                    SERIAL PRIMARY KEY,
club_id               VARCHAR,
club_name             VARCHAR,
season                VARCHAR,
competition           VARCHAR,
yellow_cards          INTEGER,
red_cards             INTEGER,
fouls_committed       INTEGER,
fouls_drawn           INTEGER,
offsides              INTEGER,
penalties_won         INTEGER,
penalties_conceded    INTEGER,
own_goals             INTEGER,
set_piece_xg_for      NUMERIC(6,2),
set_piece_xg_against  NUMERIC(6,2),
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_match_results`
One row per match. Bridges Tier A and Tier C — results go back as far as available, advanced columns only populated from 2021-22.
```sql
id                    SERIAL PRIMARY KEY,
match_id              VARCHAR UNIQUE,
season                VARCHAR,
competition           VARCHAR,
matchweek             INTEGER,
date                  DATE,
venue_id              VARCHAR,
home_club_id          VARCHAR,
away_club_id          VARCHAR,
home_goals            INTEGER,
away_goals            INTEGER,
home_xg               NUMERIC(5,2),      -- NULL pre-2021-22
away_xg               NUMERIC(5,2),      -- NULL pre-2021-22
home_possession       NUMERIC(5,2),      -- NULL pre-2021-22
away_possession       NUMERIC(5,2),      -- NULL pre-2021-22
attendance            INTEGER,
referee               VARCHAR,
match_report_url      VARCHAR,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_match_team_stats`
One row per team per match. Tier C — 2021-22 floor.
```sql
id                    SERIAL PRIMARY KEY,
match_id              VARCHAR,
club_id               VARCHAR,
season                VARCHAR,
competition           VARCHAR,
home_away             VARCHAR,           -- home, away
shots                 INTEGER,
shots_on_target       INTEGER,
xg                    NUMERIC(5,2),
npxg                  NUMERIC(5,2),
xa                    NUMERIC(5,2),
passes_completed      INTEGER,
passes_attempted      INTEGER,
pass_completion_pct   NUMERIC(5,2),
progressive_passes    INTEGER,
key_passes            INTEGER,
pressures             INTEGER,
ppda                  NUMERIC(6,3),
tackles               INTEGER,
interceptions         INTEGER,
progressive_carries   INTEGER,
touches_att_third     INTEGER,
fouls                 INTEGER,
yellow_cards          INTEGER,
red_cards             INTEGER,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_match_player_stats`
One row per player per match. Tier C — 2021-22 floor.
```sql
id                    SERIAL PRIMARY KEY,
match_id              VARCHAR,
player_id             VARCHAR,
player_name           VARCHAR,
club_id               VARCHAR,
season                VARCHAR,
competition           VARCHAR,
position              VARCHAR,
minutes_played        INTEGER,
goals                 INTEGER,
assists               INTEGER,
xg                    NUMERIC(5,2),
xa                    NUMERIC(5,2),
npxg                  NUMERIC(5,2),
shots                 INTEGER,
shots_on_target       INTEGER,
passes_completed      INTEGER,
passes_attempted      INTEGER,
progressive_passes    INTEGER,
key_passes            INTEGER,
pressures             INTEGER,
tackles               INTEGER,
interceptions         INTEGER,
progressive_carries   INTEGER,
take_ons_attempted    INTEGER,
take_ons_succeeded    INTEGER,
yellow_card           BOOLEAN DEFAULT FALSE,
red_card              BOOLEAN DEFAULT FALSE,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_player_standard_stats`
One row per player per season per competition. Tier C — 2021-22 floor.
```sql
id                    SERIAL PRIMARY KEY,
player_id             VARCHAR,
player_name           VARCHAR,
club_id               VARCHAR,
season                VARCHAR,
competition           VARCHAR,
nationality           VARCHAR,
position              VARCHAR,
age                   INTEGER,
matches_played        INTEGER,
starts                INTEGER,
minutes_played        INTEGER,
goals                 INTEGER,
assists               INTEGER,
yellow_cards          INTEGER,
red_cards             INTEGER,
xg                    NUMERIC(6,2),
npxg                  NUMERIC(6,2),
xa                    NUMERIC(6,2),
goals_per_90          NUMERIC(5,3),
assists_per_90        NUMERIC(5,3),
xg_per_90             NUMERIC(5,3),
xa_per_90             NUMERIC(5,3),
npxg_per_90           NUMERIC(5,3),
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_player_shooting`
```sql
id                    SERIAL PRIMARY KEY,
player_id             VARCHAR,
player_name           VARCHAR,
club_id               VARCHAR,
season                VARCHAR,
competition           VARCHAR,
shots                 INTEGER,
shots_on_target       INTEGER,
shots_on_target_pct   NUMERIC(5,2),
goals                 INTEGER,
xg                    NUMERIC(6,2),
npxg                  NUMERIC(6,2),
avg_shot_distance     NUMERIC(5,2),
shots_from_free_kicks INTEGER,
npxg_per_shot         NUMERIC(5,3),
goals_minus_xg        NUMERIC(6,2),
npxg_minus_goals      NUMERIC(6,2),
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_player_passing`
```sql
id                    SERIAL PRIMARY KEY,
player_id             VARCHAR,
player_name           VARCHAR,
club_id               VARCHAR,
season                VARCHAR,
competition           VARCHAR,
passes_completed      INTEGER,
passes_attempted      INTEGER,
pass_completion_pct   NUMERIC(5,2),
progressive_passes    INTEGER,
progressive_pass_yards INTEGER,
passes_final_third    INTEGER,
passes_penalty_area   INTEGER,
key_passes            INTEGER,
xa                    NUMERIC(6,2),
crosses               INTEGER,
corner_kicks          INTEGER,
passes_offside        INTEGER,
passes_blocked        INTEGER,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_player_defensive`
```sql
id                    SERIAL PRIMARY KEY,
player_id             VARCHAR,
player_name           VARCHAR,
club_id               VARCHAR,
season                VARCHAR,
competition           VARCHAR,
tackles               INTEGER,
tackles_won           INTEGER,
pressures             INTEGER,
pressure_success_rate NUMERIC(5,2),
pressure_regains      INTEGER,
pressures_def_third   INTEGER,
pressures_mid_third   INTEGER,
pressures_att_third   INTEGER,
blocks                INTEGER,
interceptions         INTEGER,
clearances            INTEGER,
errors_leading_to_shot INTEGER,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_player_possession`
```sql
id                    SERIAL PRIMARY KEY,
player_id             VARCHAR,
player_name           VARCHAR,
club_id               VARCHAR,
season                VARCHAR,
competition           VARCHAR,
touches               INTEGER,
touches_def_third     INTEGER,
touches_mid_third     INTEGER,
touches_att_third     INTEGER,
touches_penalty_area  INTEGER,
progressive_carries   INTEGER,
carry_distance        INTEGER,
carries_final_third   INTEGER,
carries_penalty_area  INTEGER,
take_ons_attempted    INTEGER,
take_ons_succeeded    INTEGER,
take_on_pct           NUMERIC(5,2),
miscontrols           INTEGER,
dispossessed          INTEGER,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fbref_player_misc`
```sql
id                    SERIAL PRIMARY KEY,
player_id             VARCHAR,
player_name           VARCHAR,
club_id               VARCHAR,
season                VARCHAR,
competition           VARCHAR,
yellow_cards          INTEGER,
red_cards             INTEGER,
second_yellow         INTEGER,
fouls_committed       INTEGER,
fouls_drawn           INTEGER,
offsides              INTEGER,
penalties_won         INTEGER,
penalties_conceded    INTEGER,
own_goals             INTEGER,
recoveries            INTEGER,
aerial_duels_won      INTEGER,
aerial_duels_lost     INTEGER,
aerial_duel_pct       NUMERIC(5,2),
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

### FOOTBALL-DATA.ORG TABLES

---

#### `euro_raw.fdorg_matches`
Tier A spine — goes back as far as football-data.org has data.
```sql
id                    SERIAL PRIMARY KEY,
match_id              VARCHAR UNIQUE,
season                VARCHAR,
competition_id        VARCHAR,
matchweek             INTEGER,
date                  TIMESTAMP,
status                VARCHAR,           -- SCHEDULED, FINISHED, POSTPONED
home_club_id          VARCHAR,
away_club_id          VARCHAR,
home_goals            INTEGER,
away_goals            INTEGER,
home_goals_ht         INTEGER,
away_goals_ht         INTEGER,
winner                VARCHAR,           -- HOME_TEAM, AWAY_TEAM, DRAW
stage                 VARCHAR,
data_source           VARCHAR DEFAULT 'football-data.org',
source_match_id       VARCHAR,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fdorg_standings`
One row per club per matchweek per season. Tier A.
```sql
id                    SERIAL PRIMARY KEY,
season                VARCHAR,
competition_id        VARCHAR,
matchweek             INTEGER,
club_id               VARCHAR,
position              INTEGER,
played                INTEGER,
won                   INTEGER,
drawn                 INTEGER,
lost                  INTEGER,
goals_for             INTEGER,
goals_against         INTEGER,
goal_difference       INTEGER,
points                INTEGER,
form                  VARCHAR,           -- e.g. W,W,D,L,W
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fdorg_lineups`
Tier C — 2021-22 floor (coverage inconsistent before this).
```sql
id                    SERIAL PRIMARY KEY,
match_id              VARCHAR,
club_id               VARCHAR,
player_id             VARCHAR,
player_name           VARCHAR,
position              VARCHAR,
shirt_number          INTEGER,
is_starting           BOOLEAN,
is_captain            BOOLEAN,
substituted_in_minute INTEGER,
substituted_out_minute INTEGER,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fdorg_events`
One row per match event. Tier C — 2021-22 floor.
```sql
id                    SERIAL PRIMARY KEY,
event_id              VARCHAR UNIQUE,
match_id              VARCHAR,
minute                INTEGER,
extra_time_minute     INTEGER,
event_type            VARCHAR,           -- GOAL, YELLOW_CARD, RED_CARD, SUBSTITUTION, PENALTY
club_id               VARCHAR,
player_id             VARCHAR,
player_name           VARCHAR,
assist_player_id      VARCHAR,
assist_player_name    VARCHAR,
detail                VARCHAR,           -- e.g. Normal Goal, Own Goal, Penalty
data_source           VARCHAR DEFAULT 'football-data.org',
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fdorg_head_to_head`
Derived from match results. Tier A — deep history.
```sql
id                    SERIAL PRIMARY KEY,
club_a_id             VARCHAR,
club_b_id             VARCHAR,
competition_id        VARCHAR,
season                VARCHAR,
match_id              VARCHAR,
club_a_goals          INTEGER,
club_b_goals          INTEGER,
winner_club_id        VARCHAR,
venue_type            VARCHAR,           -- home, away, neutral
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.fdorg_competition_seasons`
Tier A — tracks competition metadata per season.
```sql
id                    SERIAL PRIMARY KEY,
competition_id        VARCHAR,
season                VARCHAR,
n_teams               INTEGER,
n_matchweeks          INTEGER,
champion_club_id      VARCHAR,
relegated_club_ids    VARCHAR[],
top_scorer_player_id  VARCHAR,
top_scorer_goals      INTEGER,
data_source           VARCHAR DEFAULT 'football-data.org',
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

### OPENFOOT BALL TABLES — Tier A (deep history)

---

#### `euro_raw.openftbl_results`
Historical results spine. Goes back as far as OpenFootball has data.
Note: Uses club names, not IDs. Name resolution to canonical clubs happens in Silver.
```sql
id                    SERIAL PRIMARY KEY,
season                VARCHAR,
competition           VARCHAR,
date                  DATE,
round                 VARCHAR,
home_club_name        VARCHAR,
away_club_name        VARCHAR,
home_goals            INTEGER,
away_goals            INTEGER,
source_file           VARCHAR,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.openftbl_competition_winners`
One row per competition per season. Tier A.
```sql
id                    SERIAL PRIMARY KEY,
season                VARCHAR,
competition           VARCHAR,
winner_club_name      VARCHAR,
runner_up_club_name   VARCHAR,
third_place_club_name VARCHAR,
top_scorer_name       VARCHAR,
top_scorer_goals      INTEGER,
source_file           VARCHAR,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

### UNDERSTAT TABLES — Tier C (2021-22 floor; extends to 2014-15 if needed)

---

#### `euro_raw.understat_match_xg`
One row per match.
```sql
id                    SERIAL PRIMARY KEY,
source_match_id       VARCHAR UNIQUE,
season                VARCHAR,
competition           VARCHAR,
date                  DATE,
home_club_name        VARCHAR,
away_club_name        VARCHAR,
home_goals            INTEGER,
away_goals            INTEGER,
home_xg               NUMERIC(5,2),
away_xg               NUMERIC(5,2),
home_forecast_win     NUMERIC(5,4),
home_forecast_draw    NUMERIC(5,4),
home_forecast_loss    NUMERIC(5,4),
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.understat_player_season_xg`
One row per player per season per competition.
```sql
id                    SERIAL PRIMARY KEY,
source_player_id      VARCHAR,
player_name           VARCHAR,
club_name             VARCHAR,
season                VARCHAR,
competition           VARCHAR,
matches               INTEGER,
minutes               INTEGER,
goals                 INTEGER,
assists               INTEGER,
xg                    NUMERIC(6,2),
xa                    NUMERIC(6,2),
npxg                  NUMERIC(6,2),
xg_per_90             NUMERIC(5,3),
xa_per_90             NUMERIC(5,3),
yellow_cards          INTEGER,
red_cards             INTEGER,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

### CLUBELO TABLE — Tier A (full history)

---

#### `euro_raw.clubelo_ratings`
One row per club per date. Updated daily via single endpoint.
```sql
id                    SERIAL PRIMARY KEY,
club_name             VARCHAR,
date                  DATE,
elo_rating            NUMERIC(7,2),
competition           VARCHAR,
rank                  INTEGER,
data_source           VARCHAR DEFAULT 'clubelo.com',
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

### TRANSFERMARKT TABLES — Tier B (no floor)

---

#### `euro_raw.transfermarkt_transfers`
One row per transfer. Full history.
```sql
id                    SERIAL PRIMARY KEY,
transfer_id           VARCHAR UNIQUE,
season                VARCHAR,
transfer_window       VARCHAR,           -- summer, winter
player_id             VARCHAR,
player_name           VARCHAR,
from_club_id          VARCHAR,
from_club_name        VARCHAR,
to_club_id            VARCHAR,
to_club_name          VARCHAR,
transfer_fee_euros    BIGINT,
transfer_type         VARCHAR,           -- permanent, loan, loan_return, free, unknown
player_age_at_transfer INTEGER,
position              VARCHAR,
source_url            VARCHAR,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.transfermarkt_valuations`
One row per player per valuation date.
```sql
id                    SERIAL PRIMARY KEY,
source_player_id      VARCHAR,
player_name           VARCHAR,
valuation_date        DATE,
market_value_euros    BIGINT,
club_id               VARCHAR,
club_name             VARCHAR,
age                   INTEGER,
position              VARCHAR,
nationality           VARCHAR,
source_url            VARCHAR,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.transfermarkt_club_spend`
One row per club per season.
```sql
id                    SERIAL PRIMARY KEY,
club_id               VARCHAR,
club_name             VARCHAR,
season                VARCHAR,
total_spend_euros     BIGINT,
total_income_euros    BIGINT,
net_spend_euros       BIGINT,
n_signings            INTEGER,
n_departures          INTEGER,
biggest_signing_fee   BIGINT,
biggest_sale_fee      BIGINT,
source_url            VARCHAR,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.transfermarkt_managers`
One row per manager tenure per club. Full history.
```sql
id                    SERIAL PRIMARY KEY,
manager_id            VARCHAR,
manager_name          VARCHAR,
nationality           VARCHAR,
club_id               VARCHAR,
club_name             VARCHAR,
competition           VARCHAR,
date_appointed        DATE,
date_left             DATE,
matches_managed       INTEGER,
wins                  INTEGER,
draws                 INTEGER,
losses                INTEGER,
win_pct               NUMERIC(5,2),
trophies_won          INTEGER,
departure_reason      VARCHAR,           -- sacked, resigned, contract_end, mutual
source_url            VARCHAR,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

#### `euro_raw.transfermarkt_squad_valuations`
One row per club per season.
```sql
id                    SERIAL PRIMARY KEY,
club_id               VARCHAR,
club_name             VARCHAR,
season                VARCHAR,
total_squad_value_euros BIGINT,
avg_player_value_euros  BIGINT,
median_player_value_euros BIGINT,
squad_size            INTEGER,
foreign_player_count  INTEGER,
source_url            VARCHAR,
ingested_at           TIMESTAMP DEFAULT NOW()
```

---

## Table Count Summary

| Source | Tables | Tier |
|---|---|---|
| Reference | 4 | Shared |
| FBref — Team | 6 | C |
| FBref — Match | 3 | A/C |
| FBref — Player | 6 | C |
| football-data.org | 5 | A/C |
| OpenFootball | 2 | A |
| Understat | 2 | C |
| ClubElo | 1 | A |
| Transfermarkt | 5 | B |
| **Total** | **34** | |

---

## Bronze Rules (Non-Negotiable)

1. Bronze tables are append-only. Never UPDATE or DELETE rows.
2. All tables carry `ingested_at TIMESTAMP DEFAULT NOW()`.
3. Deduplication and entity resolution happen in Silver, not Bronze.
4. OpenFootball club names are raw strings — Silver resolves them to canonical `club_id`.
5. Understat and Transfermarkt use `source_player_id` — Silver resolves to canonical `player_id`.
6. Tier C tables must not contain data before 2021-22 in the metric pipeline (historical FBref for Tier B context is separate).
7. No transformations, calculations, or derived columns in Bronze.
8. Source URL columns on scraped tables are mandatory for audit and re-fetch.