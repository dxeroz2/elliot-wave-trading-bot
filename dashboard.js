async function updateDashboard() {
    try {
        const response = await fetch('dashboard_data.json');
        if (!response.ok) return;
        const data = await response.json();

        // Update Header
        document.getElementById('status-badge').innerText = data.stats.current_setup.status.toUpperCase();
        document.getElementById('last-update').innerText = data.last_update;
        document.getElementById('exchange-info').innerText = `${data.exchange.toUpperCase()} (${data.testnet ? 'TESTNET' : 'LIVE'})`;

        // Update Stats
        const balance = data.stats.current_balance;
        const initial = data.stats.initial_balance;
        const pnl = balance - initial;
        const pnlPct = initial !== 0 ? (pnl / initial) * 100 : 0;

        document.getElementById('balance').innerText = `$${balance.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('initial-balance').innerText = `Initial: $${initial.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('total-pnl').innerText = `${pnl >= 0 ? '+' : ''}$${pnl.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('total-pnl').style.color = pnl >= 0 ? '#00ff88' : '#ff3366';
        document.getElementById('pnl-pct').innerText = `${pnl >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%`;

        document.getElementById('win-loss').innerText = `${data.stats.wins} / ${data.stats.losses}`;
        const totalTrades = data.stats.wins + data.stats.losses;
        const winRate = totalTrades > 0 ? (data.stats.wins / totalTrades) * 100 : 0;
        document.getElementById('win-rate').innerText = `Win Rate: ${winRate.toFixed(1)}%`;

        // Update Market Analysis
        document.getElementById('display-symbol').innerText = data.symbol;
        const biasEl = document.getElementById('macro-bias');
        biasEl.innerText = data.stats.current_setup.macro_bias;
        biasEl.className = `bias-${data.stats.current_setup.macro_bias.toLowerCase()}`;
        
        document.getElementById('setup-direction').innerText = data.stats.current_setup.direction || 'NONE';
        document.getElementById('wave-count').innerText = data.stats.current_setup.wave_count;

        // Update Active Position
        const noTradeEl = document.getElementById('no-trade');
        const tradeContentEl = document.getElementById('trade-content');
        
        if (data.active_position) {
            noTradeEl.classList.add('hidden');
            tradeContentEl.classList.remove('hidden');
            
            document.getElementById('pos-direction').innerText = data.active_position.direction;
            document.getElementById('active-trade-panel').className = `panel trade-panel ${data.active_position.direction}`;
            document.getElementById('pos-qty').innerText = `${data.active_position.total_qty.toFixed(4)} Units`;
            document.getElementById('pos-entry').innerText = `$${data.active_position.entry_price.toLocaleString()}`;
            document.getElementById('pos-tp').innerText = `$${data.active_position.tp_price.toLocaleString()}`;
            document.getElementById('pos-sl').innerText = `$${data.active_position.sl_price.toLocaleString()}`;
        } else {
            noTradeEl.classList.remove('hidden');
            tradeContentEl.classList.add('hidden');
            document.getElementById('active-trade-panel').className = 'panel trade-panel';
        }

    } catch (error) {
        console.error('Error fetching dashboard data:', error);
    }
}

// Update every 2 seconds
setInterval(updateDashboard, 2000);
updateDashboard();
