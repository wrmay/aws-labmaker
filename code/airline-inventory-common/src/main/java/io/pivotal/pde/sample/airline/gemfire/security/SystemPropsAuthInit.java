package io.pivotal.pde.sample.airline.gemfire.security;

import java.util.Properties;

import org.apache.geode.LogWriter;
import org.apache.geode.distributed.DistributedMember;
import org.apache.geode.security.AuthInitialize;
import org.apache.geode.security.AuthenticationFailedException;

public class SystemPropsAuthInit implements AuthInitialize {
	
	private LogWriter systemLogger, securityLogger;
	
	public static AuthInitialize create() { return new SystemPropsAuthInit();}
	
	@Override
	public void close() {
	}

	@Override
	public Properties getCredentials(Properties props, DistributedMember distrMember,
			boolean isPeer) throws AuthenticationFailedException {
		String username = props.getProperty("security-username");
		String password = props.getProperty("security-password");
		
		Properties result = new Properties();
		result.setProperty("username", username);
		result.setProperty("password", password);
		return result;
	}

	@Override
	public void init(LogWriter systemLogger, LogWriter securityLogger)
			throws AuthenticationFailedException {
		this.systemLogger = systemLogger;
		this.securityLogger = securityLogger;
	}

}
