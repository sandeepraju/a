-- CREATE THE transaction TABLE
CREATE TABLE transaction (
	   id BIGSERIAL PRIMARY KEY NOT NULL,
	   tstamp TIMESTAMP NOT NULL,
	   amount NUMERIC NOT NULL,
	   balance NUMERIC NOT NULL,
	   type VARCHAR(20) NOT NULL,
	   description VARCHAR(100) NOT NULL
);

