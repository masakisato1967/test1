from google.transit import gtfs_realtime_pb2
import urllib.request as ur
import urllib.error as ue
import pandas as pd
import plotly.graph_objects as go
import io
import requests
import zipfile
import streamlit as st


# 現在の運行データを取得する
file_url = "http://opendata.sagabus.info/saga-current.zip"

# ファイルとして保存せずに処理するやり方
f = io.BytesIO()
r = requests.get(file_url)
f.write(r.content)

with zipfile.ZipFile(f) as z:
    with z.open('trips.txt') as r:
        df_trips = pd.read_csv(r)



# カラムのみに空のDataFrameを作成
cols = ["id", "route_id", "url", "header_text", "description_text"]
df_alert = pd.DataFrame(columns=cols)



def get_realtime_data():
    # カラムのみに空のDataFrameを作成
    colmns = ["id", "trip_id", "latitude", "longitude", "current_stop_sequence", "timestamp", "vehicle_id"]
    df_vehicle = pd.DataFrame(columns=colmns)

    feed_vehicle = gtfs_realtime_pb2.FeedMessage()
    res = ur.urlopen('http://opendata.sagabus.info/vehicle.pb')
    feed_vehicle.ParseFromString(res.read())

    data_flg = False
    if feed_vehicle.entity:
        data_flg = True
        print('got it')
        for entity in feed_vehicle.entity:
            vehicle_data = pd.Series(
                {'id': entity.id, 'trip_id': entity.vehicle.trip.trip_id, 'latitude': entity.vehicle.position.latitude,
                 'longitude': entity.vehicle.position.longitude,
                 "current_stop_sequence": entity.vehicle.current_stop_sequence,
                 "timestamp": entity.vehicle.timestamp, "vehicle_id": entity.vehicle.vehicle.id})
            df_vehicle = df_vehicle.append(vehicle_data, ignore_index=True)
    else:
        realtime_data_message = "Out of service"
        status = False
        return status, realtime_data_message, df_vehicle

    # if there is data, execute code following
    if data_flg:
        # 運行データとリアルタイムデータをマージ（運行データに含まれる'trip_headsign'情報を利用したいため）
        df = pd.merge(df_vehicle, df_trips, on='trip_id', how='outer', indicator=True)
        df_new = df[df['_merge'] == 'both']
        # maker用のsymmbolデータを作成
        df_new['symbol'] = 'bus'

        realtime_data_message = "in operation"
        status = True
        return status, realtime_data_message, df_new


def figure_map(data_frame):
    fig2 = go.Figure(go.Scattermapbox(
        lat=data_frame['latitude'],
        lon=data_frame['longitude'],
        mode='markers + text',
        marker={'size': 20, 'symbol': data_frame['symbol']},
        # marker=go.scattermapbox.Marker(
        #     size=20
        # ),
        text=data_frame['trip_headsign'], textposition="bottom right"
    ))

    fig2.update_layout(
        title='佐賀県の路線バス情報',
        autosize=True,
        hovermode='closest',
        mapbox=dict(
            accesstoken=mapbox_access_token,
            bearing=0,
            center=dict(
                lat=data_frame['latitude'].mean(),
                lon=data_frame['longitude'].mean()
            ),
            style='streets',  # マップの種類
            pitch=0,
            zoom=10
        ),
    )
    st.plotly_chart(fig2)
    # fig2.show()


st.write('佐賀県の路線バス情報')
st.write('http://www.bus.saga.saga.jp/index.php')

status,message, dataframe = get_realtime_data()
st.write('現在の運行状況：' + message)

if status:
    figure_map(dataframe)
    st.write('GTFSデータの取得先は以下のとおりです。データ提供者サーバーの負担を軽減するため、本ページの高頻度での更新はご遠慮ください。')
    st.write('【静的データ公開事業者】')
    st.write('・佐賀市交通局・祐徳自動車株式会社・昭和自動車株式会社・佐賀市・嬉野市')
    st.write('【動的データ公開事業者】')
    st.write('・佐賀市交通局・祐徳自動車株式会社・昭和自動車株式会社')
