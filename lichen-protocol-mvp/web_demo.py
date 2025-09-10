#!/usr/bin/env python3
"""
Lichen Protocol SIS MVP Web Demo

A lightweight, single-page web interface for showcasing the hallway orchestrator
with the same scenarios as the CLI demo. Strictly demo-only with no persistence.
"""

import asyncio
import json
import sys
from typing import Dict, Any, List
from hallway import HallwayOrchestrator, run_hallway
from aiohttp import web, WSMsgType
import aiohttp_cors


class WebDemo:
    """Web demo server for the Lichen Protocol SIS MVP"""
    
    def __init__(self):
        self.contract = self._load_contract()
        self.orchestrator = HallwayOrchestrator(self.contract)
    
    def _load_contract(self) -> Dict[str, Any]:
        """Load the canonical hallway contract"""
        try:
            with open("hallway/config/hallway.contract.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("❌ Error: Could not find hallway contract file")
            print("   Make sure you're running from the repo root directory")
            sys.exit(1)
    
    async def run_full_canonical_walk(self) -> Dict[str, Any]:
        """Run the complete 7-step canonical sequence"""
        result = await self.orchestrator.run(
            session_state_ref="web-demo-full-canonical",
            options={"stop_on_decline": True},
            payloads={
                "entry_room": {"consent": "YES"},
                "diagnostic_room": {"tone": "focused", "residue": "clear"},
                "protocol_room": {"protocol_id": "clearing_entry", "depth": "full"},
                "walk_room": {
                    "protocol_id": "demo_walk",
                    "steps": [
                        {"title": "Demo Step 1", "description": "First demonstration step"},
                        {"title": "Demo Step 2", "description": "Second demonstration step"}
                    ]
                },
                "memory_room": {"tone_label": "focused", "action": "capture"},
                "integration_commit_room": {
                    "integration_notes": "Demo integration complete",
                    "session_context": "Full canonical walk demonstration"
                },
                "exit_room": {
                    "completion_confirmed": True,
                    "session_goals_met": True
                }
            }
        )
        return result
    
    async def run_mini_walk(self) -> Dict[str, Any]:
        """Run the mini walk (Entry → Exit)"""
        result = await run_hallway(
            session_state_ref="web-demo-mini-walk",
            options={"mini_walk": True},
            payloads={
                "entry_room": {"consent": "YES"},
                "exit_room": {
                    "completion_confirmed": True,
                    "session_goals_met": True
                }
            }
        )
        return result
    
    async def run_custom_subset(self) -> Dict[str, Any]:
        """Run a custom subset (Entry → Protocol → Exit)"""
        result = await run_hallway(
            session_state_ref="web-demo-custom-subset",
            options={"rooms_subset": ["entry_room", "protocol_room", "exit_room"]},
            payloads={
                "entry_room": {"consent": "YES"},
                "protocol_room": {"protocol_id": "clearing_entry", "depth": "full"},
                "exit_room": {
                    "completion_confirmed": True,
                    "session_goals_met": True
                }
            }
        )
        return result
    
    async def run_dry_run(self) -> Dict[str, Any]:
        """Run a dry run to show all available rooms"""
        result = await run_hallway(
            session_state_ref="web-demo-dry-run",
            options={"dry_run": True}
        )
        return result
    
    async def run_gate_deny(self) -> Dict[str, Any]:
        """Run a gate deny scenario to demonstrate governance"""
        # Create a custom contract with a gate that will deny
        deny_contract = self.contract.copy()
        deny_contract["sequence"] = ["entry_room", "diagnostic_room", "exit_room"]
        
        # Create a gate that denies diagnostic_room
        from hallway.gates import GateInterface, GateDecision
        
        class DemoDenyGate(GateInterface):
            def evaluate(self, room_id: str, session_state_ref: str, payload: dict = None) -> GateDecision:
                if room_id == "diagnostic_room":
                    return GateDecision(
                        gate="demo_deny_gate",
                        allow=False,
                        reason="Demo: Diagnostic room disabled for governance demonstration",
                        details={"room_id": room_id, "demo": True}
                    )
                return GateDecision(
                    gate="demo_deny_gate",
                    allow=True,
                    reason="Demo: Room allowed",
                    details={"room_id": room_id, "demo": True}
                )
        
        deny_orchestrator = HallwayOrchestrator(deny_contract, {"coherence_gate": DemoDenyGate()})
        
        result = await deny_orchestrator.run(
            session_state_ref="web-demo-gate-deny",
            options={"stop_on_decline": True},
            payloads={
                "entry_room": {"consent": "YES"},
                "exit_room": {
                    "completion_confirmed": True,
                    "session_goals_met": True
                }
            }
        )
        return result
    
    async def run_scenario(self, scenario: str) -> Dict[str, Any]:
        """Run a specific scenario"""
        scenarios = {
            "full": self.run_full_canonical_walk,
            "mini": self.run_mini_walk,
            "subset": self.run_custom_subset,
            "dry": self.run_dry_run,
            "deny": self.run_gate_deny,
        }
        
        if scenario not in scenarios:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        return await scenarios[scenario]()
    
    async def websocket_handler(self, request):
        """Handle WebSocket connections for real-time demo updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        scenario = data.get("scenario")
                        
                        if not scenario:
                            await ws.send_str(json.dumps({
                                "error": "No scenario specified"
                            }))
                            continue
                        
                        # Send start message
                        await ws.send_str(json.dumps({
                            "type": "start",
                            "scenario": scenario,
                            "message": f"Starting {scenario} scenario..."
                        }))
                        
                        # Run the scenario
                        result = await self.run_scenario(scenario)
                        
                        # Send result
                        await ws.send_str(json.dumps({
                            "type": "result",
                            "scenario": scenario,
                            "data": result
                        }))
                        
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            "error": "Invalid JSON"
                        }))
                    except Exception as e:
                        await ws.send_str(json.dumps({
                            "error": str(e)
                        }))
                elif msg.type == WSMsgType.ERROR:
                    print(f"WebSocket error: {ws.exception()}")
        
        except Exception as e:
            print(f"WebSocket handler error: {e}")
        
        return ws


def create_app():
    """Create the web application"""
    demo = WebDemo()
    
    app = web.Application()
    
    # Configure CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Add routes
    app.router.add_get('/', demo.index_handler)
    app.router.add_get('/ws', demo.websocket_handler)
    app.router.add_static('/', path='web_demo_static', name='static')
    
    # Add CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app


async def index_handler(request):
    """Serve the main demo page"""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Lichen Protocol SIS MVP Demo</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container {
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }
            h1 {
                text-align: center;
                color: #2c3e50;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            .subtitle {
                text-align: center;
                color: #7f8c8d;
                margin-bottom: 30px;
                font-size: 1.1em;
            }
            .stones {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 30px;
                border-left: 4px solid #3498db;
            }
            .stones h3 {
                margin-top: 0;
                color: #2c3e50;
            }
            .scenarios {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .scenario {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                border: 2px solid transparent;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .scenario:hover {
                border-color: #3498db;
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            }
            .scenario h3 {
                margin-top: 0;
                color: #2c3e50;
            }
            .scenario p {
                color: #7f8c8d;
                margin-bottom: 15px;
            }
            .run-btn {
                background: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                transition: background 0.3s ease;
            }
            .run-btn:hover {
                background: #2980b9;
            }
            .run-btn:disabled {
                background: #bdc3c7;
                cursor: not-allowed;
            }
            .output {
                background: #2c3e50;
                color: #ecf0f1;
                border-radius: 8px;
                padding: 20px;
                margin-top: 20px;
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 14px;
                line-height: 1.5;
                max-height: 400px;
                overflow-y: auto;
                white-space: pre-wrap;
            }
            .status {
                padding: 10px;
                border-radius: 6px;
                margin: 10px 0;
                font-weight: bold;
            }
            .status.running {
                background: #f39c12;
                color: white;
            }
            .status.success {
                background: #27ae60;
                color: white;
            }
            .status.error {
                background: #e74c3c;
                color: white;
            }
            .step {
                margin: 10px 0;
                padding: 10px;
                background: #34495e;
                border-radius: 4px;
                border-left: 4px solid #3498db;
            }
            .step.decline {
                border-left-color: #e74c3c;
            }
            .summary {
                background: #ecf0f1;
                border-radius: 8px;
                padding: 20px;
                margin-top: 20px;
            }
            .summary h3 {
                margin-top: 0;
                color: #2c3e50;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧬 Lichen Protocol SIS MVP Demo</h1>
            <p class="subtitle">Foundation Stones: Light Before Form, Speed of Trust, Presence Is Productivity, Integrity Is the Growth Strategy</p>
            
            <div class="stones">
                <h3>🏛️ Foundation Stones</h3>
                <p><strong>Light Before Form:</strong> Structured, predictable flow</p>
                <p><strong>Speed of Trust:</strong> Efficient room-to-room transitions</p>
                <p><strong>Presence Is Productivity:</strong> Focused, purposeful execution</p>
                <p><strong>Integrity Is the Growth Strategy:</strong> Validated, auditable results</p>
            </div>
            
            <div class="scenarios">
                <div class="scenario" data-scenario="full">
                    <h3>1. Full Canonical Walk</h3>
                    <p>Complete 7-step journey: Entry → Diagnostic → Protocol → Walk → Memory → Integration → Exit</p>
                    <button class="run-btn" onclick="runScenario('full')">Run Demo</button>
                </div>
                
                <div class="scenario" data-scenario="mini">
                    <h3>2. Mini Walk</h3>
                    <p>Essential flow: Entry → Exit</p>
                    <button class="run-btn" onclick="runScenario('mini')">Run Demo</button>
                </div>
                
                <div class="scenario" data-scenario="subset">
                    <h3>3. Custom Subset</h3>
                    <p>Focused exploration: Entry → Protocol → Exit</p>
                    <button class="run-btn" onclick="runScenario('subset')">Run Demo</button>
                </div>
                
                <div class="scenario" data-scenario="dry">
                    <h3>4. Dry Run</h3>
                    <p>Availability check: Show all 7 available rooms</p>
                    <button class="run-btn" onclick="runScenario('dry')">Run Demo</button>
                </div>
                
                <div class="scenario" data-scenario="deny">
                    <h3>5. Gate Deny</h3>
                    <p>Governance demonstration: Show proper decline handling</p>
                    <button class="run-btn" onclick="runScenario('deny')">Run Demo</button>
                </div>
            </div>
            
            <div id="output" style="display: none;">
                <div id="status"></div>
                <div id="steps"></div>
                <div id="summary"></div>
            </div>
        </div>
        
        <script>
            let ws = null;
            let currentScenario = null;
            
            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function() {
                    console.log('WebSocket connected');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                };
                
                ws.onclose = function() {
                    console.log('WebSocket disconnected');
                    setTimeout(connectWebSocket, 1000);
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                };
            }
            
            function handleMessage(data) {
                if (data.type === 'start') {
                    showStatus('running', `Starting ${data.scenario} scenario...`);
                    showSteps('');
                    showSummary('');
                } else if (data.type === 'result') {
                    displayResult(data.data);
                } else if (data.error) {
                    showStatus('error', `Error: ${data.error}`);
                }
            }
            
            function runScenario(scenario) {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    currentScenario = scenario;
                    document.getElementById('output').style.display = 'block';
                    ws.send(JSON.stringify({scenario: scenario}));
                } else {
                    showStatus('error', 'WebSocket not connected. Please refresh the page.');
                }
            }
            
            function showStatus(type, message) {
                const statusDiv = document.getElementById('status');
                statusDiv.className = `status ${type}`;
                statusDiv.textContent = message;
            }
            
            function showSteps(content) {
                document.getElementById('steps').innerHTML = content;
            }
            
            function showSummary(content) {
                document.getElementById('summary').innerHTML = content;
            }
            
            function displayResult(result) {
                const steps = result.outputs.steps;
                const exitSummary = result.outputs.exit_summary;
                
                // Show status
                const completed = exitSummary.completed;
                showStatus(completed ? 'success' : 'error', 
                    completed ? 'Demo completed successfully!' : 'Demo completed with decline');
                
                // Show steps
                let stepsHtml = '<h3>📋 Execution Steps</h3>';
                steps.forEach((step, index) => {
                    const status = step.status === 'ok' ? '✅' : '❌';
                    const statusClass = step.status === 'ok' ? '' : 'decline';
                    const displayText = step.data.display_text || 'No display text available';
                    const nextAction = step.data.next_action || 'unknown';
                    
                    stepsHtml += `
                        <div class="step ${statusClass}">
                            <strong>${status} Step ${index + 1}: ${step.room_id}</strong><br>
                            <strong>Action:</strong> ${nextAction}<br>
                            <strong>Output:</strong> ${displayText.substring(0, 200)}${displayText.length > 200 ? '...' : ''}
                        </div>
                    `;
                });
                showSteps(stepsHtml);
                
                // Show summary
                let summaryHtml = `
                    <h3>📊 Demo Summary</h3>
                    <p><strong>Completed:</strong> ${completed ? '✅ Yes' : '❌ No'}</p>
                    <p><strong>Steps executed:</strong> ${steps.length}</p>
                    <p><strong>Final state ref:</strong> ${result.outputs.final_state_ref}</p>
                `;
                
                if (!completed && exitSummary.decline) {
                    summaryHtml += `<p><strong>Decline reason:</strong> ${exitSummary.decline.reason}</p>`;
                }
                
                summaryHtml += `
                    <h4>🏛️ Foundation Stones Demonstrated:</h4>
                    <p>• Light Before Form: Structured, predictable flow</p>
                    <p>• Speed of Trust: Efficient room-to-room transitions</p>
                    <p>• Presence Is Productivity: Focused, purposeful execution</p>
                    <p>• Integrity Is the Growth Strategy: ${completed ? 'Validated, auditable results' : 'Proper decline handling'}</p>
                `;
                
                showSummary(summaryHtml);
            }
            
            // Connect WebSocket when page loads
            window.onload = function() {
                connectWebSocket();
            };
        </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')


# Add the index handler to the WebDemo class
WebDemo.index_handler = index_handler


async def main():
    """Main entry point for the web demo server"""
    app = create_app()
    
    print("🌐 Starting Lichen Protocol SIS MVP Web Demo...")
    print("📡 WebSocket server will be available at ws://localhost:8080/ws")
    print("🌍 Web interface will be available at http://localhost:8080")
    print("🛑 Press Ctrl+C to stop the server")
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    
    try:
        # Keep the server running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down web demo server...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Web demo server stopped. Thank you for exploring the Lichen Protocol SIS MVP!")
    except Exception as e:
        print(f"\n❌ Web demo error: {e}")
        sys.exit(1)
