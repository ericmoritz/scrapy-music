import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.lit
import java.net.URLEncoder;

object CONST {
  val APP_NAME = "Create Playlist"
  val VERSION = "1.x"
}

case class Config(
  minDate: String = "1979-01-01",
  inURL: String = "s3a://eam-scrapes/pitchfork/v=1/*/data.jsonlines",
  outURL: String = "s3a://eam-scrapes/music/top/"
)

object CreatePlaylistApp {
  val parser = new scopt.OptionParser[Config](CONST.APP_NAME) {
    head(CONST.APP_NAME, CONST.VERSION)

    arg[String]("<start-date>").action { (x, c) =>
      c.copy(minDate = x)
    }

    arg[String]("<output-url>").action { (x, c) =>
      c.copy(outURL = x)
    }
  }

  def execute(sesh: SparkSession)(conf: Config): Unit = {
    import sesh.implicits._

    val objects = sesh.read.json(
      conf.inURL
    )
    val minDate = conf.minDate
    objects.distinct.registerTempTable("objects")

    val link = sesh.udf.register("link",
      (href: String, text: String) => s"""%html <a href="$href" target="_blank">$text</a>"""
    )

    val searchURL = sesh.udf.register("searchURL",
      (x: String) => s"spotify://search:${URLEncoder.encode(x)}"
    )

    val fullReleaseName = sesh.udf.register("fullReleaseName",
      (artistName: String, albumName: String) => s"$artistName - $albumName"
    )

    val sql = s"""
SELECT DISTINCT
    review.uri as review_uri,
    release.uri as release_uri,
    album.uri as album_uri,
    rating.uri as rating_uri,
    review.url,
    review.datePublished,
    review.author,
    release.datePublished as releaseDatePublished,
    rating.ratingValue,
    album.name as albumName,
    artist.name as artistName
    FROM
      objects as review,
      objects as release,
      objects as artist,
      objects as rating,
      objects as album
      LATERAL VIEW explode(album.byArtist) a2a AS artist

    WHERE
      review.itemReviewed['@id'] = release.uri
    AND
      release.releaseOf['@id'] = album.uri
    AND
      a2a.artist['@id'] = artist.uri
    AND
      review.reviewRating['@id'] = rating.uri
    AND
      review.datePublished >= '$minDate'
    AND
      rating.ratingValue >= 650
    AND
      release.datePublished >= 2016
"""

    val reviews = sesh.sql(sql).select(
      fullReleaseName($"artistName", $"albumName").as("fullAlbumName"),
      link($"url", fullReleaseName($"artistName", $"albumName")).as("a_tag"),
      link(
        searchURL(fullReleaseName($"artistName", $"albumName")),
        lit("search")).as("search_a_tag"),
      $"*"
    )
    reviews.write.json(s"${conf.outURL}/minDate=$minDate")
  }

  def main(args: Array[String]) {
    val sesh = SparkSession.builder().getOrCreate()
    parser.parse(args, Config()).foreach(execute(sesh) _)
  }
}
