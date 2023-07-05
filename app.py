from flask import Flask, render_template, request, flash, session, redirect, url_for
import bcrypt
from flask_mysqldb import MySQL, MySQLdb
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow import keras
import matplotlib.pyplot as plt
# from tensorflow.keras.models import load_model


app = Flask(__name__)
# session
app.secret_key = 'your_secret_key_here'
# db
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'cuaca'
mysql = MySQL(app)
# Tentukan ekstensi file yang diizinkan
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

model = tf.keras.models.load_model("modelweather.h5")  # model
class_names = ["Cerah", "Berawan", "Hujan"]  # to convert class


# Fungsi untuk memeriksa ekstensi file yang diunggah
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# # Rute untuk mengunggah file
# @app.route('/upload', methods=['GET', 'POST'])
# def upload_file():
#     if request.method == 'POST':
#         # Periksa apakah file ada dalam request
#         file = request.files['file']
#         if file.filename == '':
#             flash('No file part', 'error')
#             return redirect(url_for('formdata'))
#         # Periksa apakah file yang diunggah memiliki ekstensi yang diizinkan
#         if file and allowed_file(file.filename):
#             col_name = ['arah_angin', 'kecepatan_angin',
#                         'jarak_pandang', 'suhu', 'titik_embun', 'tekanan_udara']
#             df = pd.read_csv(file, names=col_name, header=None, sep=';')

#             # Cek dan mengganti nilai nan dengan None
#             df.replace({np.nan: None}, inplace=True)

#             for i, row in df.iterrows():
#                 # Memastikan tidak ada nilai nan sebelum menyimpan ke database
#                 if any(pd.isnull(row)):
#                     flash('Invalid data in the file', 'error')
#                     return redirect(url_for('formdata'))

#                 # Simpan hasil prediksi ke dalam database
#                 cursor = mysql.connection.cursor()
#                 cursor.execute("""INSERT INTO master_cuaca (arah_angin, kecepatan_angin, jarak_pandang, suhu, titik_embun, tekanan_udara)
#                 VALUES (%s,%s,%s,%s,%s,%s)""",
#                                (row.arah_angin, row.kecepatan_angin, row.jarak_pandang, row.suhu, row.titik_embun, row.tekanan_udara))
#                 mysql.connection.commit()
#                 cursor.close()

#             flash('File uploaded successfully', 'success')
#             return redirect(url_for('datatable'))
#         else:
#             flash('Invalid file extension', 'error')
#             return redirect(url_for('formdata'))
#     return render_template("pages/datatable.html")

# Rute untuk mengunggah file
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Periksa apakah file ada dalam request
        file = request.files['file']
        if file.filename == '':
            flash('No file part', 'error')
            return redirect(url_for('formdata'))
        # Periksa apakah file yang diunggah memiliki ekstensi yang diizinkan
        if file and allowed_file(file.filename):
            col_name = ['arah_angin', 'kecepatan_angin',
                        'jarak_pandang', 'suhu', 'titik_embun', 'tekanan_udara']
            df = pd.read_csv(file, names=col_name, header=0,
                             sep=';', skipinitialspace=True)

            # Cek dan mengganti nilai nan dengan None
            df.replace({np.nan: None}, inplace=True)

            # Load the trained model
            model = tf.keras.models.load_model("modelweather.h5")  # model
            class_names = ["Cerah", "Berawan", "Hujan"]

            for i, row in df.iterrows():
                # Memastikan tidak ada nilai nan sebelum menyimpan ke database
                if any(pd.isnull(row)):
                    flash('Invalid data in the file', 'error')
                    return redirect(url_for('formdata'))
                row = row.astype(float)
                # Preprocess the input data
                input_data = row.values.reshape(1, -1)

                # Predict using the loaded model
                prediction = model.predict(input_data)
                predicted_class_index = np.argmax(prediction)
                predicted_class = class_names[predicted_class_index]

                # Insert the predicted class into the database
                cursor = mysql.connection.cursor()
                cursor.execute(
                    """INSERT INTO master_cuaca (arah_angin, kecepatan_angin, jarak_pandang, suhu, titik_embun, tekanan_udara, cuaca) 
                    VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (row.arah_angin, row.kecepatan_angin, row.jarak_pandang,
                     row.suhu, row.titik_embun, row.tekanan_udara, predicted_class)
                )
                mysql.connection.commit()
                cursor.close()

            flash('File uploaded successfully', 'success')
            return redirect(url_for('datatable'))
        else:
            flash('Invalid file extension', 'error')
            return redirect(url_for('formdata'))
    return render_template("pages/datatable.html")


# PAGE USER
@app.route("/")
def index():
    if 'username' in session:
        session.clear()
        return redirect(url_for('index'))
    else:
        # get data form
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM master_cuaca")
        data = cursor.fetchall()
        cursor.close()
        return render_template("pages/index.html", data=data)  # page index


# PAGE LOGIN
@app.route("/login", methods=['POST', 'GET'])
def login():
    if 'username' in session:
        session.clear()
        return redirect(url_for('login'))
    else:
        if request.method == "POST":
            username = request.form['username']
            password = request.form['password'].encode('utf-8')
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(
                "SELECT * FROM user WHERE username = (%s)", (username,))
            data = cursor.fetchone()
            cursor.close()

            if data is not None and len(data) > 0:
                hashed_password = bcrypt.hashpw(
                    password, data['password'].encode('utf-8'))
                if (hashed_password == data['password'].encode('utf-8')):
                    session['username'] = data['username']
                    return redirect(url_for('home'))
                else:
                    flash('username/password invalid', 'error')
                    return redirect(url_for('login'))
            else:
                flash('invalid, data not found', 'error')
                return redirect(url_for('login'))
        else:
            return render_template("pages/login.html")  # page login


# PAGE REGISTER
@app.route("/register", methods=['POST', 'GET'])
def register():
    if 'username' in session:
        session.clear()
        return redirect(url_for('register'))
    else:
        if request.method == "GET":
            return render_template("pages/register.html")
        else:
            idcard = request.form['idcard']
            email = request.form['email']
            username = request.form['username']
            password = request.form['password'].encode('utf-8')
            password = bcrypt.hashpw(password, bcrypt.gensalt())

            cursor = mysql.connection.cursor()
            cursor.execute(
                """INSERT INTO
                user (idcard, email, username, password)
                VALUES (%s,%s,%s,%s)""",
                (idcard, email, username, password))
            mysql.connection.commit()
            session['username'] = request.form['username']
            flash('successfully! username/password has been created', 'success')
            return render_template("pages/register.html")  # page register


# PAGE ADMIN
@app.route("/home")
def home():
    # grafik
    if 'username' in session:
        # Query data dari database
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT cuaca, COUNT(*) as jumlah FROM master_cuaca GROUP BY cuaca")
        data = cursor.fetchall()

        # Memisahkan label dan nilai dari hasil query
        labels = [row[0] for row in data]
        values = [row[1] for row in data]

        # Membuat grafik menggunakan Matplotlib
        # plt.pie(labels, values)
        # plt.xlabel('cuaca')
        # plt.ylabel('jumlah')
        plt.pie(values, labels=labels)
        plt.title("Jumlah Data Berdasarkan Cuaca")
        # plt.title('Data Chart')

        # Menyimpan grafik sebagai file gambar
        # plt.savefig('static/img/pie.png')
        # page home
        return render_template("pages/home.html")
    else:
        return redirect(url_for('index'))


# DATA WEATHER ADMIN
@app.route("/datatable")
def datatable():
    if 'username' in session:
        # get data form
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM master_cuaca")
        data = cursor.fetchall()
        cursor.close()
        # page datatable
        return render_template("pages/datatable.html", data=data)
    else:
        return redirect(url_for('index'))


@ app.route("/deletecuaca/<int:id_cuaca>", methods=['POST'])
def deletecuaca(id_cuaca):
    if 'username' in session:
        # delete data
        cursor = mysql.connection.cursor()
        cursor.execute(
            "DELETE FROM master_cuaca WHERE id_cuaca = (%s)", (id_cuaca,))
        mysql.connection.commit()
        cursor.close()
        return render_template("pages/datatable.html")  # page formdata
    else:
        return redirect(url_for('index'))


# FORM WEATHER ADMIN
@ app.route("/formdata")
def formdata():
    if 'username' in session:
        return render_template("pages/formdata.html")  # page formdata
    else:
        return redirect(url_for('index'))


@app.route("/editcuaca/<int:id_cuaca>", methods=['GET'])
def editcuaca(id_cuaca):
    if 'username' in session:
        # get edit data
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT * FROM master_cuaca WHERE id_cuaca = (%s)", (id_cuaca,))
        data = cursor.fetchall()
        cursor.close()
        # page edit data form
        return render_template("pages/editformdata.html", data=data)
    else:
        return redirect(url_for('index'))


@ app.route("/updatedata/<int:id_cuaca>", methods=['POST'])
def updatedata(id_cuaca):
    if 'username' in session:
        # insert data form
        tanggal = request.form['tanggal']
        pukul = request.form['pukul']
        arah_angin = float(request.form['arah_angin'])
        kecepatan_angin = float(request.form['kecepatan_angin'])
        jarak_pandang = float(request.form['jarak_pandang'])
        suhu = float(request.form['suhu'])
        titik_embun = float(request.form['titik_embun'])
        tekanan_udara = float(request.form['tekanan_udara'])
        data = {'arah_angin': [arah_angin],
                'kecepatan_angin': [kecepatan_angin],
                'jarak_pandang': [jarak_pandang],
                'suhu': [suhu],
                'titik_embun': [titik_embun],
                'tekanan_udara': [tekanan_udara]}

        df = pd.DataFrame(data)
        prediction = model.predict(df)
        predicted_index = np.argmax(prediction)
        cuaca = class_names[predicted_index]

        cursor = mysql.connection.cursor()
        cursor.execute(
            """UPDATE master_cuaca SET 
            tanggal=%s, pukul=%s, arah_angin=%s, kecepatan_angin=%s, jarak_pandang=%s, suhu=%s, titik_embun=%s, tekanan_udara=%s, cuaca=%s WHERE id_cuaca = %s""",
            (tanggal, pukul, arah_angin, kecepatan_angin, jarak_pandang, suhu, titik_embun, tekanan_udara, cuaca, id_cuaca))
        mysql.connection.commit()
        cursor.close()
        flash('Data has been updated successfully', 'success')
        # page formdata predict
        return render_template("pages/formdata.html", cuaca=cuaca, tanggal=tanggal, pukul=pukul, arah_angin=arah_angin,
                               kecepatan_angin=kecepatan_angin, jarak_pandang=jarak_pandang,
                               suhu=suhu, titik_embun=titik_embun, tekanan_udara=tekanan_udara)
    else:
        return redirect(url_for('index'))


@ app.route("/predict", methods=['POST'])
def predict():
    if 'username' in session:
        # insert data form
        tanggal = request.form['tanggal']
        pukul = request.form['pukul']
        arah_angin = float(request.form['arah_angin'])
        kecepatan_angin = float(request.form['kecepatan_angin'])
        jarak_pandang = float(request.form['jarak_pandang'])
        suhu = float(request.form['suhu'])
        titik_embun = float(request.form['titik_embun'])
        tekanan_udara = float(request.form['tekanan_udara'])
        data = {'arah_angin': [arah_angin],
                'kecepatan_angin': [kecepatan_angin],
                'jarak_pandang': [jarak_pandang],
                'suhu': [suhu],
                'titik_embun': [titik_embun],
                'tekanan_udara': [tekanan_udara]}

        df = pd.DataFrame(data)
        prediction = model.predict(df)
        predicted_index = np.argmax(prediction)
        cuaca = class_names[predicted_index]

        cursor = mysql.connection.cursor()
        cursor.execute(
            """INSERT INTO
            master_cuaca (tanggal, pukul, arah_angin, kecepatan_angin, jarak_pandang,
                        suhu, titik_embun, tekanan_udara, cuaca)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (tanggal, pukul, arah_angin, kecepatan_angin, jarak_pandang, suhu, titik_embun, tekanan_udara, cuaca))
        # db.commit()
        mysql.connection.commit()
        cursor.close()
        flash('Data has been saved successfully', 'success')
        # page formdata predict
        return render_template("pages/formdata.html", cuaca=cuaca, tanggal=tanggal, pukul=pukul, arah_angin=arah_angin,
                               kecepatan_angin=kecepatan_angin, jarak_pandang=jarak_pandang,
                               suhu=suhu, titik_embun=titik_embun, tekanan_udara=tekanan_udara)
    else:
        return redirect(url_for('index'))


# PAGE LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return render_template("pages/login.html")  # page login


if __name__ == "__main__":
    app.run(debug=True, port=8005)
