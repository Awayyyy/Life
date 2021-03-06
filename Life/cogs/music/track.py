from granitepy import objects


class Track(objects.Track):

    def __init__(self, track, data, *, ctx=None):
        super(Track, self).__init__(track, data)

        self.channel = ctx.channel
        self.requester = ctx.author
