from flask import Flask, jsonify, request
import os
import sqlite3

app = Flask(__name__)
DB_PATH = os.getenv("DB_PATH", "booking.db")


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS trips (
        trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
        mode TEXT NOT NULL,
        origin TEXT NOT NULL,
        destination TEXT NOT NULL,
        travel_date TEXT NOT NULL,
        available_seats INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS bookings (
        booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        trip_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'CONFIRMED',
        FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
    );

    CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
    );
    """)
    connection.commit()
    connection.close()


@app.get("/health")
def health():
    return jsonify(
        status="ok",
        environment=os.getenv("APP_ENV", "DEV")
    )


@app.get("/api/trips")
def search_trips():
    args = request.args
    required = ["origin", "destination", "date", "mode"]
    if any(not args.get(item) for item in required):
        return jsonify(error="origin, destination, date, and mode are required"), 400

    connection = get_db()
    rows = connection.execute(
        """SELECT * FROM trips
           WHERE origin=? AND destination=? AND travel_date=? AND mode=?""",
        (args["origin"], args["destination"], args["date"], args["mode"])
    ).fetchall()
    connection.close()
    return jsonify([dict(row) for row in rows])


@app.post("/api/trips")
def create_trip():
    data = request.get_json(force=True)
    required = ["mode", "origin", "destination", "travel_date", "available_seats"]

    if any(field not in data for field in required):
        return jsonify(error="Missing required trip field"), 400

    connection = get_db()
    cursor = connection.execute(
        """INSERT INTO trips
           (mode, origin, destination, travel_date, available_seats)
           VALUES (?, ?, ?, ?, ?)""",
        tuple(data[field] for field in required)
    )
    connection.commit()
    trip_id = cursor.lastrowid
    connection.close()

    return jsonify(trip_id=trip_id), 201


@app.post("/api/bookings")
def create_booking():
    data = request.get_json(force=True)

    if not all(field in data for field in ("user_id", "trip_id")):
        return jsonify(error="user_id and trip_id are required"), 400

    connection = get_db()
    trip = connection.execute(
        "SELECT * FROM trips WHERE trip_id=?", (data["trip_id"],)
    ).fetchone()

    if trip is None:
        connection.close()
        return jsonify(error="Trip not found"), 404

    if trip["available_seats"] < 1:
        connection.close()
        return jsonify(error="No seats available"), 409

    connection.execute(
        "UPDATE trips SET available_seats=available_seats-1 WHERE trip_id=?",
        (trip["trip_id"],)
    )
    cursor = connection.execute(
        "INSERT INTO bookings(user_id, trip_id) VALUES (?, ?)",
        (data["user_id"], trip["trip_id"])
    )
    connection.commit()
    booking_id = cursor.lastrowid
    connection.close()

    return jsonify(booking_id=booking_id, status="CONFIRMED"), 201


@app.post("/api/payments")
def process_payment():
    data = request.get_json(force=True)

    if not all(field in data for field in ("booking_id", "amount")):
        return jsonify(error="booking_id and amount are required"), 400

    connection = get_db()
    booking = connection.execute(
        "SELECT * FROM bookings WHERE booking_id=?", (data["booking_id"],)
    ).fetchone()

    if booking is None:
        connection.close()
        return jsonify(error="Booking not found"), 404

    cursor = connection.execute(
        """INSERT INTO payments(booking_id, amount, status)
           VALUES (?, ?, ?)""",
        (data["booking_id"], float(data["amount"]), "AUTHORIZED")
    )
    connection.commit()
    payment_id = cursor.lastrowid
    connection.close()

    return jsonify(payment_id=payment_id, status="AUTHORIZED"), 201


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
