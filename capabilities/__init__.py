

def get_all():
    from .weather import define as define_weather
    weather = define_weather()

    from .ask import define as define_ask
    ask = define_ask()

    from .aviation import define as define_aviation
    aviation = define_aviation()
    return [
        weather,
        ask,
        aviation
    ]