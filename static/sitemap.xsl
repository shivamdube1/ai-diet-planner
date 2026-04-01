<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" 
                xmlns:html="http://www.w3.org/TR/REC-html40"
                xmlns:sitemap="http://www.sitemaps.org/schemas/sitemap/0.9"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <html xmlns="http://www.w3.org/1999/xhtml">
      <head>
        <title>XML Sitemap — NutriAI</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&amp;display=swap" rel="stylesheet" />
        <style type="text/css">
          body {
            font-family: 'DM Sans', sans-serif;
            font-size: 14px;
            color: #f1f5f9;
            background-color: #0f172a;
            margin: 0;
            padding: 40px 20px;
          }
          .container {
            max-width: 900px;
            margin: 0 auto;
          }
          #header {
            text-align: center;
            padding-bottom: 40px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 40px;
          }
          h1 {
            color: #16a34a;
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0 0 10px 0;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
          }
          .brand-icon { font-size: 2.2rem; }
          #header p {
            color: #94a3b8;
            font-size: 1rem;
            margin: 0;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            background-color: #1e293b;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
          }
          th {
            background-color: #334155;
            color: #4ade80;
            text-align: left;
            padding: 15px 20px;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
          }
          tr {
            border-bottom: 1px solid rgba(255,255,255,0.05);
          }
          tr:hover {
            background-color: rgba(22, 163, 74, 0.05);
          }
          td {
            padding: 15px 20px;
            word-break: break-all;
          }
          a {
            color: #86efac;
            text-decoration: none;
            transition: color 0.2s;
          }
          a:hover {
            color: #16a34a;
            text-decoration: underline;
          }
          .priority {
            display: inline-block;
            padding: 4px 10px;
            background: rgba(22,163,74,0.15);
            border: 1px solid rgba(22,163,74,0.3);
            border-radius: 20px;
            font-size: 0.8rem;
            color: #4ade80;
          }
          .freq {
            color: #94a3b8;
            font-size: 0.85rem;
          }
          #footer {
            margin-top: 40px;
            text-align: center;
            color: #64748b;
            font-size: 0.8rem;
          }
        </style>
      </head>
      <body>
        <div class="container">
          <div id="header">
            <h1><span class="brand-icon">🥗</span> NutriAI</h1>
            <p>XML Sitemap Index · AI-Powered Personalized Nutrition</p>
          </div>
          <table>
            <thead>
              <tr>
                <th width="70%">URL Location</th>
                <th width="15%">Frequency</th>
                <th width="15%">Priority</th>
              </tr>
            </thead>
            <tbody>
              <xsl:for-each select="sitemap:urlset/sitemap:url">
                <tr>
                  <td>
                    <xsl:variable name="itemURL">
                      <xsl:value-of select="sitemap:loc"/>
                    </xsl:variable>
                    <a href="{$itemURL}">
                      <xsl:value-of select="sitemap:loc"/>
                    </a>
                  </td>
                  <td>
                    <span class="freq">
                      <xsl:value-of select="sitemap:changefreq"/>
                    </span>
                  </td>
                  <td>
                    <span class="priority">
                      <xsl:value-of select="sitemap:priority"/>
                    </span>
                  </td>
                </tr>
              </xsl:for-each>
            </tbody>
          </table>
          <div id="footer">
            <p>© 2025 NutriAI. Designed for Healthy Living.</p>
          </div>
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
