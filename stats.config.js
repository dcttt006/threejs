// Pitch Royale — statistics (see STATISTIEKEN.md for the setup)
//
// Fill in the two values of your own Supabase project. While they are
// empty nothing is measured and the game works as before.
//
// The key is the "anon public" (or "publishable") key. It is meant to be
// public: the table's row level security (stats.sql) only lets the game ADD
// rows, and only your own login can READ them.
// NEVER put the service_role / secret key in this file.
const STATS_CONFIG = {
    url: 'https://rgyvgdsizfrgikgsomac.supabase.co',
    key: 'sb_publishable_Y4YP209t5x_FjGDOh4_tXQ_zBhV80lq',   // publishable: safe to be public
};
