import PropTypes from 'prop-types';
import React from 'react';
import { FormattedHTMLMessage, injectIntl } from 'react-intl';
import messages from '../../../resources/messages';
import SourceOrCollectionWidget from '../../common/SourceOrCollectionWidget';
import { urlToCollection, urlToSource } from '../../../lib/urlUtil';

const localMessages = {
  title: { id: 'topic.info.title', defaultMessage: 'Version {versionNumber}: Subtopics' },
  seedQueryCount: { id: 'topic.info.seedQueryCount', defaultMessage: 'Matches {storyCount} stories already in our database.' },
  willSpider: { id: 'topic.info.willSpider', defaultMessage: 'Links will be followed to find more stories ({rounds} rounds).' },
  willNotSpider: { id: 'topic.info.willNotSpider', defaultMessage: 'Links will <em>not</em> be followed to find more stories.' },
  dates: { id: 'topic.info.dates', defaultMessage: 'Dates:' },
  datesData: { id: 'topic.info.datesData', defaultMessage: '{startDate} to {endDate}' },
};

const SubtopicQuerySummary = ({ seedQueryCount, topic, snapshot, intl, faded }) => {
  // the form has them grouped together, but the topic object has them separate
  let sourcesAndCollections = topic.media ? topic.media : topic.sourcesAndCollections;
  sourcesAndCollections = topic.media_tags ? [...sourcesAndCollections, ...topic.media_tags] : sourcesAndCollections;
  return (
    <div className={`topic-info-sidebar ${faded ? 'faded' : ''}`}>
      <h2>
        {snapshot && <FormattedHTMLMessage {...localMessages.title} values={{ versionNumber: snapshot.note }} />}
      </h2>
      <p>
        <FormattedHTMLMessage
          {...localMessages.seedQueryCount}
          values={{ storyCount: intl.formatNumber(seedQueryCount || topic.seed_query_story_count) }}
        />
        <br />
      </p>
      <p>
        <b><FormattedHTMLMessage {...messages.topicQueryProp} /></b>
        <code>{topic.solr_seed_query}</code>
      </p>
      <p>
        <b><FormattedHTMLMessage {...localMessages.dates} /></b>
        <FormattedHTMLMessage
          {...localMessages.datesData}
          values={{ startDate: topic.start_date, endDate: topic.end_date }}
        />
      </p>
      <p>
        <b><FormattedHTMLMessage {...messages.topicSourceCollectionsProp} /></b>
        {sourcesAndCollections.map(o => (
          <SourceOrCollectionWidget
            key={o.id || o.tags_id || o.media_id}
            object={o}
            link={o.tags_id ? urlToCollection(o.tags_id) : urlToSource(o.media_id)}
          />
        ))}
      </p>
    </div>
  );
};

SubtopicQuerySummary.propTypes = {
  topic: PropTypes.object.isRequired,
  snapshot: PropTypes.object,
  seedQueryCount: PropTypes.number,
  faded: PropTypes.bool,
  intl: PropTypes.object.isRequired,
};

export default injectIntl(SubtopicQuerySummary);
