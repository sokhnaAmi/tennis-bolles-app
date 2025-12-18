/**
 * Script de bootstrap pour initialiser la base de données
 * À exécuter une fois pour importer data.json dans PostgreSQL
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { neon } from '@neondatabase/serverless';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function bootstrap() {
  const databaseUrl = process.env.DATABASE_URL;
  
  if (!databaseUrl) {
    console.error('DATABASE_URL n\'est pas défini dans les variables d\'environnement');
    process.exit(1);
  }

  const sql = neon(databaseUrl);

  try {
    console.log('Création des tables...');
    
    // Créer les tables
    await sql`
      CREATE TABLE IF NOT EXISTS categories (
        id        INTEGER PRIMARY KEY,
        categorie TEXT    NOT NULL,
        question  TEXT    NOT NULL,
        reponse   TEXT    NOT NULL
      );
    `;
    
    await sql`
      CREATE TABLE IF NOT EXISTS bris (
        id         INTEGER PRIMARY KEY,
        affirmation TEXT   NOT NULL,
        reponse     TEXT   NOT NULL
      );
    `;
    
    await sql`
      CREATE TABLE IF NOT EXISTS admin_settings (
        id integer PRIMARY KEY,
        admin_secret text NOT NULL
      );
    `;

    console.log('Vérification des données existantes...');
    
    // Vérifier si les tables sont déjà remplies
    const countCat = await sql`SELECT COUNT(*) as count FROM categories;`;
    const countBris = await sql`SELECT COUNT(*) as count FROM bris;`;
    
    const nbCat = countCat[0]?.count || 0;
    const nbBris = countBris[0]?.count || 0;

    if (nbCat > 0 || nbBris > 0) {
      console.log(`Les données existent déjà (${nbCat} catégories, ${nbBris} bris).`);
      console.log('Pour réimporter, videz d\'abord les tables.');
      return;
    }

    console.log('Chargement de data.json...');
    
    // Charger data.json
    const dataPath = join(__dirname, '..', 'data.json');
    const dataContent = readFileSync(dataPath, 'utf-8');
    const data = JSON.parse(dataContent);

    const cats = data.categories || [];
    const bris = data.bris || [];

    console.log(`Import de ${cats.length} catégories et ${bris.length} bris...`);

    // Insérer les catégories
    if (cats.length > 0) {
      for (const c of cats) {
        await sql`
          INSERT INTO categories (id, categorie, question, reponse)
          VALUES (${c.id}, ${c.categorie}, ${c.question}, ${c.reponse});
        `;
      }
      console.log(`✓ ${cats.length} catégories importées`);
    }

    // Insérer les bris
    if (bris.length > 0) {
      for (const b of bris) {
        await sql`
          INSERT INTO bris (id, affirmation, reponse)
          VALUES (${b.id}, ${b.affirmation}, ${b.reponse});
        `;
      }
      console.log(`✓ ${bris.length} bris importés`);
    }

    // Initialiser le mot de passe admin
    const defaultSecret = process.env.ADMIN_SECRET || 'change-me-please';
    await sql`
      INSERT INTO admin_settings (id, admin_secret)
      VALUES (1, ${defaultSecret})
      ON CONFLICT (id) DO NOTHING;
    `;

    console.log('✓ Bootstrap terminé avec succès!');
  } catch (error) {
    console.error('Erreur lors du bootstrap:', error);
    process.exit(1);
  }
}

bootstrap();


