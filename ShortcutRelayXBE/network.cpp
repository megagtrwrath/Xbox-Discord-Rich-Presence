#include "stdafx.h"
#include "network.h"
#include "socketUtility.h"
#include "xboxInternals.h"

void network::init()
{
	static bool initialized = false;

	if ((XNetGetEthernetLinkStatus() & XNET_ETHERNET_LINK_ACTIVE) > 0 && !initialized)
	{
		configure();

		XNetStartupParams xnsp;
		memset(&xnsp, 0, sizeof(xnsp));
		xnsp.cfgSizeOfStruct = sizeof(XNetStartupParams);
		xnsp.cfgFlags = XNET_STARTUP_BYPASS_SECURITY;

		xnsp.cfgPrivatePoolSizeInPages = 64;
		xnsp.cfgEnetReceiveQueueLength = 16;
		xnsp.cfgIpFragMaxSimultaneous = 16;
		xnsp.cfgIpFragMaxPacketDiv256 = 32;
		xnsp.cfgSockMaxSockets = 64;

		xnsp.cfgSockDefaultRecvBufsizeInK = RECV_SOCKET_BUFFER_SIZE_IN_K;
		xnsp.cfgSockDefaultSendBufsizeInK = SEND_SOCKET_BUFFER_SIZE_IN_K;

		XNetStartup(&xnsp);

		WSADATA wsaData;
		const int result = WSAStartup(MAKEWORD(2, 2), &wsaData);

		initialized = true;
	}
}

void network::configure()
{
	XNetConfigParams netConfigParams;   
	XNetLoadConfigParams(&netConfigParams);
	bool isXboxVersion2 = netConfigParams.V2_Tag == 0x58425632;
	uint32_t* primaryDns = isXboxVersion2 ? &netConfigParams.V2_DNS1 : &netConfigParams.V1_DNS1;
	uint32_t* secondaryDns = isXboxVersion2 ? &netConfigParams.V2_DNS2 : &netConfigParams.V1_DNS2;

	if (*primaryDns == 0)
		*primaryDns = inet_addr("8.8.8.8");
	if (*secondaryDns == 0)
		*secondaryDns = inet_addr("1.1.1.1");

	// no need to mark dirty or save; we're not making changes
}

void network::restart()
{
	WSACleanup();
	XNetCleanup();
	init();
}

bool network::isReady()
{
	XNADDR addr;
	memset(&addr, 0, sizeof(addr));
	DWORD dwState = XNetGetTitleXnAddr(&addr);
	return dwState != XNET_GET_XNADDR_PENDING;
}

uint32_t network::getAddress()
{
	XNetConfigStatus status;
	memset(&status, 0, sizeof(status));
	XNetGetConfigStatus(&status);
	return status.ina.S_un.S_addr;
}

uint32_t network::getSubnet()
{
	XNetConfigStatus status;
	memset(&status, 0, sizeof(status));
	XNetGetConfigStatus(&status);
	return status.inaMask.S_un.S_addr;
}

uint32_t network::getGateway()
{
	XNetConfigStatus status;
	memset(&status, 0, sizeof(status));
	XNetGetConfigStatus(&status);
	return status.inaGateway.S_un.S_addr;
}

uint32_t network::getPrimaryDns()
{
	XNetConfigStatus status;
	memset(&status, 0, sizeof(status));
	XNetGetConfigStatus(&status);
	return status.inaDnsSecondary.S_un.S_addr;
}

uint32_t network::getSecondaryDns()
{
	XNetConfigStatus status;
	memset(&status, 0, sizeof(status));
	XNetGetConfigStatus(&status);
	return status.inaDnsSecondary.S_un.S_addr;
}
