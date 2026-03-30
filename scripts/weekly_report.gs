// ============================================================
// RAPPORT HEBDOMADAIRE CEO — Google Apps Script
// ============================================================
// CONFIGURATION : remplis les 2 valeurs ci-dessous

const SLACK_WEBHOOK_URL = "COLLE_TON_SLACK_WEBHOOK_ICI";
const ANTHROPIC_API_KEY = "COLLE_TA_CLE_ANTHROPIC_ICI";

// ============================================================

const TIMEZONE = "America/Montreal";

// Mapping couleur → catégorie (Google Apps Script EventColor)
const COLOR_TO_CATEGORY = {
  "1":  "Opérations",          // Lavande
  "2":  "Formation",            // Sauge (vert)
  "3":  "Rocks",                // Mauve (violet)
  "4":  "Meeting",              // Rouge pâle
  "5":  "Personnel",            // Jaune
  "6":  "Meeting",              // Orange
  "7":  "Acquisition Clients",  // Cyan (bleu)
  "8":  "Rencontre Clients",    // Gris
  "9":  "Acquisition Clients",  // Bleu foncé
  "10": "Formation",            // Vert foncé
  "11": "Rencontre Clients",    // Rouge
};

const EXCLUDED = new Set(["Personnel"]);

const CATEGORIES = [
  "Acquisition Clients",
  "Opérations",
  "Rencontre Clients",
  "Meeting",
  "Rocks",
  "Formation",
  "Personnel",
];

// ============================================================
// POINT D'ENTRÉE PRINCIPAL
// ============================================================

function envoyerRapportHebdo() {
  const { debut, fin } = getDerniéreSemaine();
  Logger.log(`Période : ${Utilities.formatDate(debut, TIMEZONE, "yyyy-MM-dd")} → ${Utilities.formatDate(fin, TIMEZONE, "yyyy-MM-dd")}`);

  const evenements = getEvenements(debut, fin);
  Logger.log(`${evenements.length} événements récupérés`);

  // Tente d'utiliser les couleurs
  const { heures, avecCouleur, sansCouleur } = calculerHeuresParCouleur(evenements);
  Logger.log(`Avec couleur: ${avecCouleur}, sans couleur: ${sansCouleur}`);

  let heuresFinales;

  // Si moins de 20% des événements ont une couleur → utilise Claude pour classifier
  if (avecCouleur < evenements.length * 0.2) {
    Logger.log("Peu de couleurs détectées → classification par Claude");
    heuresFinales = classifierAvecClaude(evenements);
  } else {
    heuresFinales = heures;
  }

  const totalHeures = Object.values(heuresFinales).reduce((a, b) => a + b, 0);
  Logger.log(`Total heures travaillées : ${totalHeures.toFixed(1)}h`);

  if (totalHeures === 0) {
    Logger.log("Aucune heure enregistrée — rapport non envoyé.");
    return;
  }

  const conseil = getConseilClaude(heuresFinales, totalHeures);
  envoyerSlack(heuresFinales, totalHeures, conseil, debut, fin);
  Logger.log("✅ Message Slack envoyé!");
}

// ============================================================
// CALENDRIER
// ============================================================

function getDerniéreSemaine() {
  const maintenant = new Date();
  const jourSemaine = maintenant.getDay(); // 0=dim, 1=lun...
  const jourDepuisLundi = (jourSemaine === 0) ? 6 : jourSemaine - 1;

  const lundi = new Date(maintenant);
  lundi.setDate(maintenant.getDate() - jourDepuisLundi - 7);
  lundi.setHours(0, 0, 0, 0);

  const dimanche = new Date(lundi);
  dimanche.setDate(lundi.getDate() + 6);
  dimanche.setHours(23, 59, 59, 999);

  return { debut: lundi, fin: dimanche };
}

function getEvenements(debut, fin) {
  const calendrier = CalendarApp.getDefaultCalendar();
  return calendrier.getEvents(debut, fin);
}

function calculerHeuresParCouleur(evenements) {
  const heures = {};
  let avecCouleur = 0;
  let sansCouleur = 0;

  for (const event of evenements) {
    const duree = (event.getEndTime() - event.getStartTime()) / 3600000;
    if (duree <= 0) continue;

    const couleur = event.getColor(); // ex: "3", "7", "" si défaut
    const categorie = COLOR_TO_CATEGORY[couleur];

    if (!couleur || !categorie) {
      sansCouleur++;
      continue;
    }

    avecCouleur++;

    if (EXCLUDED.has(categorie)) continue;

    heures[categorie] = (heures[categorie] || 0) + duree;
  }

  return { heures, avecCouleur, sansCouleur };
}

// ============================================================
// CLASSIFICATION PAR CLAUDE (fallback)
// ============================================================

function classifierAvecClaude(evenements) {
  const titresUniques = [...new Set(
    evenements
      .filter(e => (e.getEndTime() - e.getStartTime()) > 0)
      .map(e => e.getTitle() || "Sans titre")
  )];

  const categoriesStr = CATEGORIES.map(c => `- ${c}`).join("\n");
  const titresStr = titresUniques.map(t => `- ${t}`).join("\n");

  const prompt = `Tu es un assistant qui classifie des événements d'agenda pour un CEO.

Catégories disponibles :
${categoriesStr}

Titres des événements de la semaine :
${titresStr}

Pour chaque titre, assigne la catégorie la plus appropriée.
Utilise exactement le nom de la catégorie tel qu'écrit.
Réponds UNIQUEMENT avec un objet JSON valide.
Format : {"titre": "Catégorie", ...}`;

  const reponse = appelClaude(prompt, 1500);
  let mapping;
  try {
    let texte = reponse.trim();
    if (texte.startsWith("```")) {
      texte = texte.split("```")[1].replace(/^json/, "").trim();
    }
    mapping = JSON.parse(texte);
  } catch (e) {
    Logger.log("Erreur parsing JSON Claude: " + e);
    return {};
  }

  const heures = {};
  for (const event of evenements) {
    const duree = (event.getEndTime() - event.getStartTime()) / 3600000;
    if (duree <= 0) continue;

    const titre = event.getTitle() || "Sans titre";
    const categorie = mapping[titre] || "Autre";

    if (EXCLUDED.has(categorie)) continue;

    heures[categorie] = (heures[categorie] || 0) + duree;
  }

  return heures;
}

// ============================================================
// CONSEIL CEO VIA CLAUDE
// ============================================================

function getConseilClaude(heures, totalHeures) {
  const triees = Object.entries(heures).sort((a, b) => b[1] - a[1]);
  const breakdown = triees.map(([cat, h]) => `  - ${cat}: ${h.toFixed(1)}h`).join("\n");

  const prompt = `Tu es un consultant senior spécialisé en croissance de PME.

Contexte : CEO d'une entreprise qui génère 1M$/an, 4 employés.
Objectif : scaler significativement cette année. Le CEO est encore impliqué dans presque tout.

Répartition du temps cette semaine (total: ${totalHeures.toFixed(1)}h) :
${breakdown}

Donne un conseil court et percutant (3 phrases max).
Identifie ce qui freine la croissance ou ce qu'il devrait déléguer.
Sois direct, concret et actionnable. Réponds en français.`;

  return appelClaude(prompt, 400);
}

function appelClaude(prompt, maxTokens) {
  const payload = {
    model: "claude-opus-4-6",
    max_tokens: maxTokens,
    messages: [{ role: "user", content: prompt }]
  };

  const options = {
    method: "post",
    contentType: "application/json",
    headers: {
      "x-api-key": ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01"
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  const reponse = UrlFetchApp.fetch("https://api.anthropic.com/v1/messages", options);
  const data = JSON.parse(reponse.getContentText());

  if (data.error) {
    Logger.log("Erreur Claude: " + JSON.stringify(data.error));
    return "Conseil non disponible.";
  }

  return data.content[0].text;
}

// ============================================================
// SLACK
// ============================================================

function envoyerSlack(heures, totalHeures, conseil, debut, fin) {
  const triees = Object.entries(heures).sort((a, b) => b[1] - a[1]);

  const lignes = triees.map(([cat, h]) => {
    const barLen = Math.round((h / totalHeures) * 12);
    const bar = "█".repeat(barLen) + "░".repeat(12 - barLen);
    const pct = Math.round(h / totalHeures * 100);
    return `\`${bar}\` *${cat}* — ${h.toFixed(1)}h (${pct}%)`;
  }).join("\n");

  const formatDate = d => Utilities.formatDate(d, TIMEZONE, "d MMM");
  const semaine = `${formatDate(debut)} – ${formatDate(fin)}`;

  const blocks = [
    {
      type: "header",
      text: { type: "plain_text", text: `Rapport hebdo — ${semaine}` }
    },
    {
      type: "section",
      text: {
        type: "mrkdwn",
        text: `*Total : ${totalHeures.toFixed(1)}h travaillées*\n\n${lignes}`
      }
    },
    { type: "divider" },
    {
      type: "section",
      text: { type: "mrkdwn", text: `Conseil :\n${conseil}` }
    }
  ];

  const options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({ blocks }),
    muteHttpExceptions: true
  };

  UrlFetchApp.fetch(SLACK_WEBHOOK_URL, options);
}

// ============================================================
// DÉCLENCHEUR AUTOMATIQUE — exécute une fois pour installer
// ============================================================

function installerDeclencheur() {
  // Supprime les anciens déclencheurs
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));

  // Lundi matin à 6h
  ScriptApp.newTrigger("envoyerRapportHebdo")
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(6)
    .create();

  Logger.log("✅ Déclencheur installé : chaque lundi à 6h");
}
