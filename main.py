import discord
from discord.ext import commands, tasks
import requests
import os
import ssl
import certifi
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

ssl_context = ssl.create_default_context(cafile=certifi.where())

TOKEN = os.getenv("DISCORD_BOT_TOKEN") 
PREFIX = "!"

intents = discord.Intents.default()
intents.message_content = True  
bot = commands.Bot(command_prefix=PREFIX, intents=intents)


def fetch_btc_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() 
        data = response.json()
        return data.get("bitcoin", {}).get("usd")
    except requests.RequestException as e:
        print(f"Error fetching BTC price: {e}")
        return None


@bot.command(name="btc_profit",
             help="Calculate your profit or loss on BTC with leverage.")
async def btc_profit(ctx,
                     initial_investment: float,
                     purchase_price: float,
                     leverage: int = 1):
    current_price = fetch_btc_price()
    if current_price is None:
        await ctx.author.send("❌ Unable to fetch BTC price. Please try again later.")
        return

    if leverage < 1:
        await ctx.author.send("⚠️ Leverage must be at least 1x (no leverage).")
        return

    quantity = (initial_investment * leverage) / purchase_price
    current_value = quantity * current_price
    profit_loss = current_value - (initial_investment * leverage)
    profit_loss_status = "Profit" if profit_loss >= 0 else "Loss"

    liquidation_price = purchase_price * (1 - (1 / leverage)) if leverage > 1 else None
    liquidation_warning = (
        f"⚠️ **Liquidation Risk!** If BTC drops below **${liquidation_price:,.2f}**, you may be liquidated!"
        if liquidation_price and current_price > liquidation_price else "")

    embed = discord.Embed(
        title="📈 BTC Leverage Profit/Loss Calculator",
        description="Here is your Bitcoin investment analysis with leverage:",
        color=discord.Color.green() if profit_loss >= 0 else discord.Color.red())
    embed.add_field(name="Initial Investment", value=f"${initial_investment:,.2f}", inline=True)
    embed.add_field(name="Leverage", value=f"{leverage}x", inline=True)
    embed.add_field(name="Total Trading Amount", value=f"${initial_investment * leverage:,.2f}", inline=True)
    embed.add_field(name="Purchase Price", value=f"${purchase_price:,.2f} per BTC", inline=True)
    embed.add_field(name="Current BTC Price", value=f"${current_price:,.2f}", inline=False)
    embed.add_field(name="BTC Quantity", value=f"{quantity:,.6f} BTC", inline=True)
    embed.add_field(name="Current Value", value=f"${current_value:,.2f}", inline=True)
    embed.add_field(name=f"**{profit_loss_status}**", value=f"${profit_loss:,.2f}", inline=False)

    if liquidation_warning:
        embed.add_field(name="⚠️ Liquidation Warning", value=liquidation_warning, inline=False)

    embed.set_footer(text="Powered by CoinGecko API | Leverage trading is risky!")

    try:
        await ctx.author.send(embed=embed)  
        await ctx.message.add_reaction("📩")
    except discord.Forbidden:
        await ctx.send("❌ I can't DM you! Please enable DMs in your privacy settings.")


@bot.command(name="btc_manual",
             help="Calculate your profit or loss on BTC with a custom exit price.")
async def btc_manual(ctx,
                     initial_investment: float,
                     purchase_price: float,
                     exit_price: float,
                     leverage: int = 1):
    if leverage < 1:
        await ctx.author.send("⚠️ Leverage must be at least 1x (no leverage).")
        return

    quantity = (initial_investment * leverage) / purchase_price
    final_value = quantity * exit_price
    profit_loss = final_value - (initial_investment * leverage)
    profit_loss_status = "Profit" if profit_loss >= 0 else "Loss"

    liquidation_price = purchase_price * (1 - (1 / leverage)) if leverage > 1 else None
    liquidation_warning = (
        f"⚠️ **Liquidation Risk!** If BTC drops below **${liquidation_price:,.2f}**, you may be liquidated!"
        if liquidation_price and exit_price > liquidation_price else "")

    embed = discord.Embed(
        title="📊 BTC Manual Profit/Loss Calculator",
        description="Here is your Bitcoin investment analysis with a manual exit price:",
        color=discord.Color.green() if profit_loss >= 0 else discord.Color.red())
    embed.add_field(name="Initial Investment", value=f"${initial_investment:,.2f}", inline=True)
    embed.add_field(name="Leverage", value=f"{leverage}x", inline=True)
    embed.add_field(name="Total Trading Amount", value=f"${initial_investment * leverage:,.2f}", inline=True)
    embed.add_field(name="Purchase Price", value=f"${purchase_price:,.2f} per BTC", inline=True)
    embed.add_field(name="Exit Price", value=f"${exit_price:,.2f} per BTC", inline=False)
    embed.add_field(name="BTC Quantity", value=f"{quantity:,.6f} BTC", inline=True)
    embed.add_field(name="Final Value", value=f"${final_value:,.2f}", inline=True)
    embed.add_field(name=f"**{profit_loss_status}**", value=f"${profit_loss:,.2f}", inline=False)

    if liquidation_warning:
        embed.add_field(name="⚠️ Liquidation Warning", value=liquidation_warning, inline=False)

    embed.set_footer(text="Manual BTC Profit Calculator | Leverage trading is risky!")

    try:
        await ctx.author.send(embed=embed)
        await ctx.message.add_reaction("📩")
    except discord.Forbidden:
        await ctx.send("❌ I can't DM you! Please enable DMs in your privacy settings.")


@bot.command(name="btc_double",
             help="Calculate the BTC price where you double your initial investment with leverage.")
async def btc_double(ctx,
                     initial_investment: float,
                     entry_price: float,
                     leverage: int = 1):
    if leverage < 1:
        await ctx.author.send("⚠️ Leverage must be at least 1x (no leverage).")
        return

    total_buying_power = initial_investment * leverage
    btc_quantity = total_buying_power / entry_price

    target_value = total_buying_power + initial_investment
    target_price = target_value / btc_quantity

    current_price = fetch_btc_price()
    price_status = (
        "✅ Current price is above your target! You’ve already doubled your money!"
        if current_price and current_price >= target_price else
        "⏳ Current price is below your target. Waiting to double your money."
    )

    liquidation_price = entry_price * (1 - (1 / leverage)) if leverage > 1 else None
    liquidation_warning = (
        f"⚠️ **Liquidation Risk!** If BTC drops below **${liquidation_price:,.2f}**, you may be liquidated!"
        if liquidation_price and target_price > liquidation_price else ""
    )

    embed = discord.Embed(
        title="💰 BTC Double Money Calculator",
        description="Here’s the BTC price where you’ll double your initial investment:",
        color=discord.Color.gold()
    )
    embed.add_field(name="Initial Investment", value=f"${initial_investment:,.2f}", inline=True)
    embed.add_field(name="Leverage", value=f"{leverage}x", inline=True)
    embed.add_field(name="Total Buying Power", value=f"${total_buying_power:,.2f}", inline=True)
    embed.add_field(name="Entry Price", value=f"${entry_price:,.2f} per BTC", inline=True)
    embed.add_field(name="BTC Quantity", value=f"{btc_quantity:,.6f} BTC", inline=True)
    embed.add_field(name="Target Value (2x)", value=f"${target_value:,.2f}", inline=True)
    embed.add_field(name="**Target Price**", value=f"${target_price:,.2f} per BTC", inline=False)

    if current_price:
        embed.add_field(name="Current BTC Price", value=f"${current_price:,.2f}", inline=False)
        embed.add_field(name="Status", value=price_status, inline=False)

    if liquidation_warning:
        embed.add_field(name="⚠️ Liquidation Warning", value=liquidation_warning, inline=False)

    embed.set_footer(text="Powered by CoinGecko API | Plan your exit wisely!")

    try:
        await ctx.author.send(embed=embed)
        await ctx.message.add_reaction("📩")
    except discord.Forbidden:
        await ctx.send("❌ I can’t DM you! Please enable DMs in your privacy settings.")


@bot.command(name="commands", help="Show available commands.")
async def custom_help(ctx):
    embed = discord.Embed(title="📜 Profit BTC Bot Commands",
                          description="Here are the available commands:",
                          color=discord.Color.blue())
    embed.add_field(
        name="!btc_profit <investment> <purchase_price> <leverage>",
        value="Calculates your profit or loss based on your BTC investment.",
        inline=False)
    embed.add_field(
        name="!btc_manual <investment> <purchase_price> <exit_price> <leverage>",
        value="Calculates profit/loss with a custom exit price instead of fetching live data.",
        inline=False)
    embed.add_field(
        name="!btc_double <investment> <entry_price> <leverage>",
        value="Calculates the BTC price where you double your initial investment.",
        inline=False)
    embed.add_field(name="!commands",
                    value="Shows this help message.",
                    inline=False)
    embed.set_footer(
        text="Use the commands with the prefix '!' or type '!commands' for help"
    )

    try:
        await ctx.author.send(embed=embed)
        await ctx.message.add_reaction("📩")
    except discord.Forbidden:
        await ctx.send("❌ I can't DM you! Please enable DMs in your privacy settings.")


@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    activity = discord.Game(name="BTC Profit Analysis 💹")
    await bot.change_presence(status=discord.Status.online, activity=activity)


bot.run(TOKEN)

class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_http_server():
    server = HTTPServer(('0.0.0.0', 3000), KeepAliveHandler)
    server.serve_forever()

threading.Thread(target=run_http_server).start()
