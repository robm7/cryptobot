import fs from 'fs';
import path from 'path';

// Path to the configuration file
const configPath = path.join(process.cwd(), '..', 'config', 'cryptobot_config.json');

export default async function handler(req, res) {
  // Check authentication (in a real app, you'd use a middleware for this)
  if (!req.headers.authorization) {
    return res.status(401).json({ message: 'Unauthorized' });
  }

  try {
    // GET request to fetch the configuration
    if (req.method === 'GET') {
      // Read the configuration file
      const configData = fs.readFileSync(configPath, 'utf8');
      const config = JSON.parse(configData);
      
      return res.status(200).json(config);
    }
    
    // POST request to update the configuration
    if (req.method === 'POST') {
      // Validate the configuration against the schema (simplified for this example)
      const config = req.body;
      
      if (!config || !config.services || !config.database || !config.logging) {
        return res.status(400).json({ message: 'Invalid configuration format' });
      }
      
      // Write the configuration to the file
      fs.writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf8');
      
      return res.status(200).json({ message: 'Configuration saved successfully' });
    }
    
    // Method not allowed
    return res.status(405).json({ message: 'Method not allowed' });
  } catch (error) {
    console.error('Error handling configuration:', error);
    return res.status(500).json({ message: 'Internal server error', error: error.message });
  }
}