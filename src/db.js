/**
 * Fonctions de connexion et gestion de la base de données PostgreSQL (Neon)
 */

/**
 * Crée une connexion SQL à la base de données Neon
 * @param {string} databaseUrl - URL de connexion PostgreSQL
 * @returns {Promise<Function>} - Fonction SQL tag
 */
export async function getSQL(databaseUrl) {
  // Neon supporte les connexions HTTP depuis Cloudflare Workers
  // On utilise @neondatabase/serverless qui fonctionne avec Workers
  const { neon } = await import('@neondatabase/serverless');
  return neon(databaseUrl);
}

/**
 * Initialise les tables si elles n'existent pas
 * @param {string} databaseUrl - URL de connexion PostgreSQL
 */
export async function ensureTables(databaseUrl) {
  const sql = await getSQL(databaseUrl);
  
  // Créer la table categories
  await sql`
    CREATE TABLE IF NOT EXISTS categories (
      id        INTEGER PRIMARY KEY,
      categorie TEXT    NOT NULL,
      question  TEXT    NOT NULL,
      reponse   TEXT    NOT NULL
    );
  `;
  
  // Créer la table bris
  await sql`
    CREATE TABLE IF NOT EXISTS bris (
      id         INTEGER PRIMARY KEY,
      affirmation TEXT   NOT NULL,
      reponse     TEXT   NOT NULL
    );
  `;
  
  // Créer la table admin_settings
  await sql`
    CREATE TABLE IF NOT EXISTS admin_settings (
      id integer PRIMARY KEY,
      admin_secret text NOT NULL
    );
  `;
}

/**
 * Charge le mot de passe admin depuis la base de données
 * @param {string} databaseUrl - URL de connexion PostgreSQL
 * @param {string} defaultSecret - Mot de passe par défaut
 * @returns {Promise<string>} - Mot de passe admin
 */
export async function loadAdminSecret(databaseUrl, defaultSecret = 'change-me-please') {
  try {
    await ensureTables(databaseUrl);
    const sql = await getSQL(databaseUrl);
    
    // Vérifier si un mot de passe existe
    const result = await sql`
      SELECT admin_secret FROM admin_settings WHERE id = 1;
    `;
    
    if (result && result.length > 0 && result[0].admin_secret) {
      return result[0].admin_secret.trim();
    }
    
    // Si aucun mot de passe, créer avec la valeur par défaut
    await sql`
      INSERT INTO admin_settings (id, admin_secret)
      VALUES (1, ${defaultSecret})
      ON CONFLICT (id) DO NOTHING;
    `;
    
    return defaultSecret.trim();
  } catch (error) {
    console.error('Erreur loadAdminSecret:', error);
    return defaultSecret.trim();
  }
}

/**
 * Sauvegarde le mot de passe admin dans la base de données
 * @param {string} databaseUrl - URL de connexion PostgreSQL
 * @param {string} newSecret - Nouveau mot de passe
 */
export async function saveAdminSecret(databaseUrl, newSecret) {
  try {
    const sql = await getSQL(databaseUrl);
    await sql`
      INSERT INTO admin_settings (id, admin_secret)
      VALUES (1, ${newSecret.trim()})
      ON CONFLICT (id) DO UPDATE
      SET admin_secret = EXCLUDED.admin_secret;
    `;
  } catch (error) {
    console.error('Erreur saveAdminSecret:', error);
    throw error;
  }
}

