const express = require('express');
const app = express();
const PORT = 3000;

const osc = require('node-osc');
const oscPort = 5000;  // Define the OSC port you want to listen to

let oscData = null;  // A variable to hold the received OSC data

// Setting up the OSC server to listen for messages
const oscServer = new osc.Server(oscPort, '0.0.0.0');
oscServer.on("message", function (msg, rinfo) {
    console.log("Received OSC message:", msg);
    oscData = msg;  // Update the variable with the received message
});

// Server request to display OSC data in the browser
app.get('/', (req, res) => {
    res.send(oscData ? `Received OSC data: ${JSON.stringify(oscData)}` : 'No OSC data received yet.');
});

const os = require('os');

function getLocalIP() {
    const interfaces = os.networkInterfaces();
    for (const iface of Object.values(interfaces)) {
        for (const alias of iface) {
            if (alias.family === 'IPv4' && !alias.internal) {
                return alias.address;
            }
        }
    }
    return '0.0.0.0';
}

const localIP = getLocalIP();
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server is running on http://${localIP}:${PORT}`);
    console.log(`Listening for OSC messages on port ${oscPort}`);
});
